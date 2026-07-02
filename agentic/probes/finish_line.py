from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from agentic.app.server import create_static_app
from agentic.artifacts import ArtifactKind, ArtifactStore
from agentic.artifacts.report_quality import evaluate_report_quality
from agentic.channels.ntfy import NtfyChannel, NtfyConfig
from agentic.config.settings import AppConfig
from agentic.delivery import DeliveryStatus, DeliveryStore, ReportDeliveryService
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.resources.store import ResourceStore
from agentic.runtime.heartbeat import Watchdog
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.task_router import TaskRouter
from agentic.runtime.tick import RuntimeTickService
from agentic.scheduler import ScheduleStore, SchedulerRunner
from agentic.sources import SourceRuntime, SourceStore
from agentic.sources.discovery import SOURCE_DISCOVERY_TASK_KIND, SourceDiscoveryExecutor
from agentic.sources.strategy_recovery import (
    SOURCE_STRATEGY_RECOVERY_TASK_KIND,
    SourceStrategyRecoveryEnqueuer,
    SourceStrategyRecoveryExecutor,
)
from agentic.tasks.store import TaskStore
from agentic.tooling import ToolingBacklogStore
from agentic.synthesis.report import ModelReportSynthesizer, ReportSynthesizer
from agentic.workflow_kernel import WorkflowBuilder, WorkflowInterpreter, WorkflowStore


DEFAULT_FINISH_LINE_REQUEST = "반복 자동화 하나 만들어서 나한테 ntfy 알림 보내줘"
DEFAULT_FINISH_LINE_ANSWERS = [
    "주식갤을 소스로 써. 최근 게시글을 수집해서 개인 투자 아이디어와 시장 심리 신호를 보고 싶어.",
    "1분마다 수집하고 1시간마다 최근 글을 분석해서 트렌드 보고서로 보내줘.",
]
DEFAULT_FINISH_LINE_SOURCE_URL = "https://gall.dcinside.com/board/lists/?id=stock_new2"
DEFAULT_FINISH_LINE_ALIASES = ["community_web", "주식갤", "dcinside-gallery"]


@dataclass(frozen=True)
class FinishLineBenchmarkResult:
    ok: bool
    score_0_100: int
    state_dir: str
    request: str
    answers: list[str]
    workflow_id: str = ""
    session_id: str = ""
    planning_session_id: str = ""
    source_id: str = ""
    run_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    delivery_ids: list[str] = field(default_factory=list)
    session_event_types: list[str] = field(default_factory=list)
    report_quality: dict[str, Any] = field(default_factory=dict)
    report_synthesis: dict[str, Any] = field(default_factory=dict)
    tick: dict[str, Any] = field(default_factory=dict)
    blocker: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "score_0_100": self.score_0_100,
            "state_dir": self.state_dir,
            "request": self.request,
            "answers": self.answers,
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "planning_session_id": self.planning_session_id,
            "source_id": self.source_id,
            "run_ids": self.run_ids,
            "task_ids": self.task_ids,
            "artifact_ids": self.artifact_ids,
            "delivery_ids": self.delivery_ids,
            "session_event_types": self.session_event_types,
            "report_quality": self.report_quality,
            "report_synthesis": self.report_synthesis,
            "tick": self.tick,
            "blocker": self.blocker,
        }


def run_frontdoor_finish_line_benchmark(
    config: AppConfig,
    *,
    state_dir: str | Path | None = None,
    request: str = DEFAULT_FINISH_LINE_REQUEST,
    answers: list[str] | None = None,
    source_url: str = DEFAULT_FINISH_LINE_SOURCE_URL,
    source_name: str = "Live DCInside stock gallery",
    source_aliases: list[str] | None = None,
    ntfy_topic: str = "",
    ntfy_server: str = "https://ntfy.sh",
    web_url: str = "http://127.0.0.1:8765",
    timeout_s: float = 120.0,
    require_delivery: bool = True,
    synthesis_model_id: str = "",
    synthesis_max_tokens: int = 384,
    require_model_synthesis: bool = False,
    preseed_source: bool = True,
    source_discovery_model_id: str = "",
) -> FinishLineBenchmarkResult:
    root = Path(state_dir) if state_dir else config.trace_dir / "state" / "finish_line"
    root.mkdir(parents=True, exist_ok=True)
    selected_answers = list(answers or DEFAULT_FINISH_LINE_ANSWERS)
    aliases = list(source_aliases or DEFAULT_FINISH_LINE_ALIASES)
    app = create_static_app(
        root,
        config=config,
        source_discovery_model_id=source_discovery_model_id,
    )

    if preseed_source:
        asyncio.run(
            _request(
                app,
                "POST",
                "/sources/web",
                {
                    "name": source_name,
                    "url": source_url,
                    "aliases": ",".join(aliases),
                },
            )
        )
    design_status, _ = asyncio.run(
        _request(app, "POST", "/workflows/design", {"message": request})
    )
    if design_status != 303:
        return _failed(root, request, selected_answers, f"workflow design route returned {design_status}")

    for answer in selected_answers:
        sessions = _json_response(asyncio.run(_request(app, "GET", "/planning-sessions")))
        open_sessions = [item for item in sessions if item.get("question")]
        if not open_sessions:
            break
        session_id = str(open_sessions[0]["session_id"])
        status, _ = asyncio.run(
            _request(
                app,
                "POST",
                f"/planning-sessions/{session_id}/answer",
                {"answer": answer},
            )
        )
        if status != 303:
            return _failed(root, request, selected_answers, f"planning answer route returned {status}")

    workflows = _json_response(asyncio.run(_request(app, "GET", "/workflows")))
    workflow = workflows[0] if workflows else {}
    workflow_id = str(workflow.get("workflow_id") or "")
    session_id = str((workflow.get("inputs") or {}).get("session_log_id") or "")
    planning_session_id = str((workflow.get("inputs") or {}).get("planning_session_id") or "")
    source_ids = list((workflow.get("inputs") or {}).get("source_ids") or [])
    source_id = str(source_ids[0]) if source_ids else ""
    if not workflow_id:
        return _failed(root, request, selected_answers, "workflow was not created")
    if require_delivery and not ntfy_topic:
        return _result(
            root,
            request,
            selected_answers,
            workflow_id=workflow_id,
            session_id=session_id,
            planning_session_id=planning_session_id,
            source_id=source_id,
            ok=False,
            score=82,
            blocker="ntfy topic is required for finish-line delivery verification",
        )

    tick = _run_ticks_until_finished(
        root,
        ntfy_topic=ntfy_topic,
        ntfy_server=ntfy_server,
        web_url=web_url,
        timeout_s=timeout_s,
        config=config,
        synthesis_model_id=synthesis_model_id,
        synthesis_max_tokens=synthesis_max_tokens,
        max_ticks=5 if not preseed_source else 3,
    )
    workflow = _latest_workflow(root, workflow_id)
    source_ids = list((workflow.get("inputs") or {}).get("source_ids") or [])
    source_id = str(source_ids[0]) if source_ids else source_id
    if workflow.get("status") != "active" and not _has_finish_line_artifact(root):
        return _result(
            root,
            request,
            selected_answers,
            workflow_id=workflow_id,
            session_id=session_id,
            planning_session_id=planning_session_id,
            source_id=source_id,
            tick=tick,
            ok=False,
            score=72,
            blocker=f"workflow status is {workflow.get('status')}",
        )
    return _result(
        root,
        request,
        selected_answers,
        workflow_id=workflow_id,
        session_id=session_id,
        planning_session_id=planning_session_id,
        source_id=source_id,
        tick=tick,
        require_delivery=require_delivery,
        require_model_synthesis=require_model_synthesis,
    )


async def _request(app: Any, method: str, path: str, data: dict[str, str] | None = None) -> tuple[int, bytes]:
    body = urlencode(data or {}).encode("utf-8")
    headers = []
    if data is not None:
        headers.append((b"content-type", b"application/x-www-form-urlencoded"))

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    payload = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return int(status), payload


def _json_response(response: tuple[int, bytes]) -> list[dict[str, Any]]:
    status, payload = response
    if status != 200:
        return []
    return list(json.loads(payload.decode("utf-8") or "[]"))


def _run_ticks_until_finished(
    state_dir: Path,
    *,
    ntfy_topic: str,
    ntfy_server: str,
    web_url: str,
    timeout_s: float,
    config: AppConfig,
    synthesis_model_id: str,
    synthesis_max_tokens: int,
    max_ticks: int,
) -> dict[str, Any]:
    task_store = TaskStore(state_dir / "agentic.sqlite3")
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    artifact_store = ArtifactStore(state_dir / "artifacts.sqlite3")
    tooling_store = ToolingBacklogStore(state_dir / "tooling.sqlite3")
    task_pool = TaskPool(
        store=task_store,
        executor=TaskRouter(
            {
                SOURCE_DISCOVERY_TASK_KIND: SourceDiscoveryExecutor(
                    config=config,
                    default_state_dir=state_dir,
                ),
                SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                    default_state_dir=state_dir,
                )
            }
        ),
        max_workers=1,
    )
    ntfy_channel = (
        NtfyChannel(
            NtfyConfig(
                enabled=True,
                server=ntfy_server,
                topic=ntfy_topic,
                title="Agentic report ready",
                web_url=web_url,
            )
        )
        if ntfy_topic
        else None
    )
    report_synthesizer = _build_report_synthesizer(
        config,
        synthesis_model_id=synthesis_model_id,
        synthesis_max_tokens=synthesis_max_tokens,
    )
    scheduler = SchedulerRunner(
        schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
        workflow_store=workflow_store,
        builder=WorkflowBuilder(
            WorkflowInterpreter(
                workflow_store=workflow_store,
                artifact_store=artifact_store,
                source_runtime=SourceRuntime(source_store=source_store, resource_store=resource_store),
                resource_store=resource_store,
                tooling_store=tooling_store,
                source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                    task_store=task_store,
                    state_dir=state_dir,
                    report_synthesis_model_id=synthesis_model_id,
                    report_synthesis_config_path=str(config.config_path),
                    report_synthesis_max_tokens=synthesis_max_tokens,
                ),
                report_synthesizer=report_synthesizer,
            )
        ),
    )
    tick = RuntimeTickService(
        task_pool=task_pool,
        watchdog=Watchdog(task_store),
        scheduler=scheduler,
        report_delivery=ReportDeliveryService(
            artifact_store=artifact_store,
            delivery_store=DeliveryStore(state_dir / "deliveries.sqlite3"),
            ntfy_channel=ntfy_channel,
            web_url=web_url,
        ),
    )
    try:
        ticks: list[dict[str, Any]] = []
        for _ in range(max(1, max_ticks)):
            result = tick.run_once(wait=True, timeout_s=timeout_s).to_record()
            ticks.append(result)
            if _has_finish_line_artifact(state_dir):
                break
        return {
            "ok": all(item.get("ok") for item in ticks),
            "ticks": ticks,
            "last": ticks[-1] if ticks else {},
        }
    finally:
        task_pool.shutdown(wait=True)


def _has_finish_line_artifact(state_dir: Path) -> bool:
    artifacts = ArtifactStore(state_dir / "artifacts.sqlite3").list(kind=ArtifactKind.REPORT, limit=1)
    return bool(artifacts)


def _latest_workflow(state_dir: Path, workflow_id: str) -> dict[str, Any]:
    if not workflow_id:
        return {}
    try:
        return WorkflowStore(state_dir / "workflows.sqlite3").get_spec(workflow_id).to_record()
    except Exception:
        return {}


def _failed(
    state_dir: Path,
    request: str,
    answers: list[str],
    blocker: str,
) -> FinishLineBenchmarkResult:
    return _result(
        state_dir,
        request,
        answers,
        ok=False,
        score=0,
        blocker=blocker,
    )


def _result(
    state_dir: Path,
    request: str,
    answers: list[str],
    *,
    workflow_id: str = "",
    session_id: str = "",
    planning_session_id: str = "",
    source_id: str = "",
    tick: dict[str, Any] | None = None,
    ok: bool | None = None,
    score: int | None = None,
    blocker: str = "",
    require_delivery: bool = True,
    require_model_synthesis: bool = False,
) -> FinishLineBenchmarkResult:
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    task_store = TaskStore(state_dir / "agentic.sqlite3")
    artifact_store = ArtifactStore(state_dir / "artifacts.sqlite3")
    delivery_store = DeliveryStore(state_dir / "deliveries.sqlite3")
    if workflow_id and not source_id:
        try:
            workflow = workflow_store.get_spec(workflow_id)
            source_ids = list((workflow.inputs or {}).get("source_ids") or [])
            source_id = str(source_ids[0]) if source_ids else ""
        except Exception:
            source_id = ""
    run_ids = [run.run_id for run in workflow_store.list_runs(limit=20)]
    task_ids = [task.task_id for task in task_store.list_tasks(limit=20)]
    artifact_ids = [artifact.artifact_id for artifact in artifact_store.list(kind=ArtifactKind.REPORT, limit=20)]
    report_quality = _latest_report_quality(artifact_store)
    report_synthesis = _latest_report_synthesis(artifact_store)
    deliveries = delivery_store.list(limit=20)
    sent_delivery_ids = [
        delivery.delivery_id
        for delivery in deliveries
        if delivery.status == DeliveryStatus.SENT
    ]
    session_event_types = _session_event_types(state_dir, session_id)
    observed_answer_count = session_event_types.count("interview_answer")
    finished = bool(sent_delivery_ids) if require_delivery else bool(artifact_ids)
    report_quality_ok = bool(report_quality.get("ok"))
    report_synthesis_ok = bool(report_synthesis.get("ok"))
    enough_interview = observed_answer_count >= 2
    computed_ok = bool(
        workflow_id
        and session_id
        and enough_interview
        and finished
        and report_quality_ok
        and (report_synthesis_ok or not require_model_synthesis)
        and not blocker
    )
    if ok is None:
        ok = computed_ok
    if score is None:
        if ok:
            score = 100 if require_model_synthesis and report_synthesis_ok else 98
        elif workflow_id and session_id and enough_interview:
            score = 88
        elif workflow_id and session_id:
            score = 80
        elif workflow_id:
            score = 70
        else:
            score = 45
    if not blocker:
        if not enough_interview:
            blocker = "session log does not contain at least two interview answers"
        elif not artifact_ids:
            blocker = "no report artifact"
        elif not report_quality_ok:
            score_text = report_quality.get("score", "unknown")
            reasons = ",".join(str(reason) for reason in report_quality.get("reasons", []))
            blocker = f"report quality gate failed score={score_text} reasons={reasons}"
        elif require_model_synthesis and not report_synthesis_ok:
            blocker = f"report synthesis gate failed error={report_synthesis.get('error') or 'missing'}"
        elif require_delivery and not sent_delivery_ids:
            blocker = "no sent delivery record"
    return FinishLineBenchmarkResult(
        ok=ok,
        score_0_100=score,
        state_dir=str(state_dir),
        request=request,
        answers=answers,
        workflow_id=workflow_id,
        session_id=session_id,
        planning_session_id=planning_session_id,
        source_id=source_id,
        run_ids=run_ids,
        task_ids=task_ids,
        artifact_ids=artifact_ids,
        delivery_ids=sent_delivery_ids,
        session_event_types=session_event_types,
        report_quality=report_quality,
        report_synthesis=report_synthesis,
        tick=tick or {},
        blocker="" if ok else blocker,
    )


def _session_event_types(state_dir: Path, session_id: str) -> list[str]:
    if not session_id:
        return []
    from agentic.sessions import SessionLogStore

    store = SessionLogStore(state_dir / "sessions.sqlite3")
    return [event.event_type for event in store.list_events(session_id, limit=1000)]


def _latest_report_quality(artifact_store: ArtifactStore) -> dict[str, Any]:
    artifacts = artifact_store.list(kind=ArtifactKind.REPORT, limit=1)
    if not artifacts:
        return {}
    artifact = artifacts[0]
    quality = (artifact.metadata or {}).get("report_quality")
    if isinstance(quality, dict):
        return dict(quality)
    return evaluate_report_quality(artifact.content).to_record()


def _latest_report_synthesis(artifact_store: ArtifactStore) -> dict[str, Any]:
    artifacts = artifact_store.list(kind=ArtifactKind.REPORT, limit=1)
    if not artifacts:
        return {}
    synthesis = (artifacts[0].metadata or {}).get("report_synthesis")
    return dict(synthesis) if isinstance(synthesis, dict) else {}


def _build_report_synthesizer(
    config: AppConfig,
    *,
    synthesis_model_id: str,
    synthesis_max_tokens: int,
) -> ReportSynthesizer | None:
    if not synthesis_model_id:
        return None
    model = config.model(synthesis_model_id)
    provider = LocalGGUFProvider(model)
    if synthesis_max_tokens > 0:
        provider = provider.with_max_tokens(synthesis_max_tokens)
    return ModelReportSynthesizer(provider)
