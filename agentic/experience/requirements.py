from __future__ import annotations

import tempfile
from pathlib import Path

from agentic.artifacts import ArtifactStore
from agentic.config.settings import AppConfig
from agentic.experience.models import (
    ExperienceEvent,
    ExperienceEventType,
    RequirementProbe,
    RequirementProbeResult,
    RequirementSmokeResult,
)
from agentic.experience.store import ExperienceStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceRuntime, SourceStore
from agentic.tooling import ToolingBacklogStore, ToolingPlanner
from agentic.workflow_kernel import (
    CapabilityPlanner,
    IntentType,
    PlanningSessionStore,
    StepType,
    WorkflowBuilder,
    WorkflowDesigner,
    WorkflowInterpreter,
    WorkflowStatus,
    WorkflowStore,
)
from agentic.workflow_kernel.source_binding import bind_checked_in_local_source


USER_REQUIREMENT_PROBES: tuple[RequirementProbe, ...] = (
    RequirementProbe(
        probe_id="wsj_newsletter_analysis",
        title="WSJ newsletter goal-based analysis",
        request="매일 Gmail로 온 WSJ 뉴스레터를 읽고 보유 주식과 스타트업 아이디어 관점에서 보고서를 만들어줘",
        expected_pattern="scheduled mail ingestion -> grounded analysis -> report",
        tags=["newsletter", "gmail", "analysis"],
    ),
    RequirementProbe(
        probe_id="social_trend_crawler",
        title="Stock community trend crawler",
        request="1분마다 주식갤과 미국 주식 reddit 최근 글을 모아서 트렌드 보고서를 만들어줘",
        expected_pattern="scheduled feed/community collection -> dedupe -> trend report",
        tags=["crawler", "social_trend", "scheduler"],
    ),
    RequirementProbe(
        probe_id="idea_memory_synthesis",
        title="Idea capture and synthesis",
        request="내 아이디어 메모를 받아서 태깅하고 기존 아이디어와 연결한 뒤 주기적으로 영감 보고서를 만들어줘",
        expected_pattern="channel capture -> memory/resource linking -> synthesis report",
        tags=["memory", "ideas", "obsidian"],
    ),
    RequirementProbe(
        probe_id="harness_self_improvement",
        title="Harness self-improvement coding workflow",
        request="이 repo를 분석해서 agentic harness가 스스로 개선할 작업을 찾고 테스트까지 돌리는 workflow를 만들어줘",
        expected_pattern="repo inspect -> plan -> patch/test proposal -> report",
        tags=["coding", "self_improvement", "repo"],
    ),
    RequirementProbe(
        probe_id="browser_ticket_transaction",
        title="Login-gated browser transaction",
        request="MSI 2026 결승전 표 예매해줘",
        continuation_answer="2장, 20만원 이하, 중앙 좌석 선호, 결제와 예매확정 전에는 반드시 승인 받아.",
        expected_pattern="planning interview -> browser observe/action -> approval -> retry watcher",
        tags=["browser", "ticketing", "approval", "watcher"],
    ),
    RequirementProbe(
        probe_id="mobile_approval_notification",
        title="Mobile approval and notification loop",
        request="승인이 필요한 작업이 생기면 ntfy로 알려주고 모바일에서 승인할 수 있게 해줘",
        continuation_answer="승인 이벤트와 채널 이벤트를 소스로 보고, ntfy 알림과 웹 승인 UI를 결과로 다뤄줘.",
        expected_pattern="approval request -> notification -> mobile/web approval",
        tags=["channel", "ntfy", "approval"],
    ),
)


def run_requirement_smoke(
    config: AppConfig,
    *,
    state_dir: str | Path | None = None,
    experience_path: str | Path | None = None,
    persist_experience: bool = True,
) -> RequirementSmokeResult:
    tempdir: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)
    else:
        root = Path(state_dir)
        root.mkdir(parents=True, exist_ok=True)
    exp_path = Path(experience_path) if experience_path is not None else config.trace_dir / "experience.jsonl"
    store = ExperienceStore(exp_path) if persist_experience else None
    try:
        results = [_run_probe(config, root, probe, store) for probe in USER_REQUIREMENT_PROBES]
        return RequirementSmokeResult(
            ok=all(result.ok for result in results),
            state_dir=str(root),
            experience_path=str(exp_path) if persist_experience else None,
            results=results,
        )
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def _run_probe(
    config: AppConfig,
    root: Path,
    probe: RequirementProbe,
    experience_store: ExperienceStore | None,
) -> RequirementProbeResult:
    workflow_store = WorkflowStore(root / "workflows.sqlite3")
    planning_store = PlanningSessionStore(root / "planning_sessions.sqlite3")
    tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
    artifact_store = ArtifactStore(root / "artifacts.sqlite3")
    source_store = SourceStore(root / "sources.sqlite3")
    resource_store = ResourceStore(root / "resources.sqlite3")
    source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
    designer = WorkflowDesigner()
    proposal = designer.design(probe.request)
    planning_store.upsert(proposal.session)
    if proposal.spec is None and probe.continuation_answer:
        proposal = designer.continue_design(proposal.session, probe.continuation_answer)
        planning_store.upsert(proposal.session)

    bottlenecks: list[str] = []
    lessons: list[str] = []
    workflow_id: str | None = None
    run_id: str | None = None
    status = proposal.session.status
    level = "needs_input"
    ok = False
    tooling_records: list[dict[str, object]] = []

    if proposal.spec is None:
        bottlenecks.append(f"planning_missing_slots:{','.join(proposal.session.missing_slots)}")
        lessons.append("The harness must preserve and answer design sessions before execution.")
    else:
        spec = bind_checked_in_local_source(proposal.spec, source_store=source_store)
        stored = workflow_store.create_spec(spec)
        workflow_id = stored.workflow_id
        capability_plan = CapabilityPlanner().plan(stored)
        tooling_plan = ToolingPlanner().plan(capability_plan)
        tooling_store.add_many(tooling_plan.requests)
        tooling_records = [request.to_record() for request in tooling_plan.requests]
        bottlenecks.extend(_bottlenecks_from_capabilities(tooling_records))
        bottlenecks.extend(_heuristic_bottlenecks(probe, stored))
        if any(request["kind"] in {"connector", "tool", "runtime"} for request in tooling_records):
            level = "blocked_by_tooling"
            lessons.append("Capability gaps should become buildable tooling backlog before retrying the workflow.")
        elif capability_plan.requires_approval:
            level = "blocked_by_approval"
            lessons.append("Sensitive or externally visible capabilities correctly stop at approval.")
        else:
            workflow_store.transition_spec(stored.workflow_id, WorkflowStatus.APPROVED)
            active = workflow_store.transition_spec(stored.workflow_id, WorkflowStatus.ACTIVE)
            builder = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=source_runtime,
                    resource_store=resource_store,
                )
            )
            execution = builder.run_approved(active, trigger={"type": "requirement_smoke", "probe": probe.probe_id})
            run_id = execution.run.run_id
            status = execution.run.status.value
            level = "completed" if execution.ok else "runtime_blocked"
            ok = execution.ok
            if execution.ok:
                lessons.append("This requirement can run through current checked-in local-source workflow primitives.")
            else:
                bottlenecks.append(str(execution.run.error or {}))
                lessons.append("The workflow is representable but the interpreter still lacks one or more execution steps.")
        if level in {"blocked_by_tooling", "blocked_by_approval"}:
            ok = True
            status = level

    result = RequirementProbeResult(
        probe=probe,
        level=level,
        ok=ok,
        intent=proposal.session.intent.intent_type.value,
        status=status,
        workflow_id=workflow_id,
        run_id=run_id,
        bottlenecks=bottlenecks,
        tooling_requests=tooling_records,
        lessons=lessons,
    )
    if experience_store is not None:
        experience_store.append(
            ExperienceEvent(
                event_type=ExperienceEventType.REQUIREMENT_PROBE,
                subject=probe.probe_id,
                summary=f"{probe.title}: {level}",
                evidence=result.to_record(),
                lessons=lessons,
                tags=probe.tags,
            )
        )
    return result


def _bottlenecks_from_capabilities(tooling_records: list[dict[str, object]]) -> list[str]:
    return [
        f"{record.get('kind')}:{record.get('capability')}:{record.get('reason')}"
        for record in tooling_records
    ]


def _heuristic_bottlenecks(probe: RequirementProbe, spec) -> list[str]:
    bottlenecks: list[str] = []
    step_types = {step.step_type for step in spec.steps}
    if probe.probe_id == "harness_self_improvement" and not (
        StepType.RUN_SCRIPT in step_types or StepType.CALL_TOOL in step_types
    ):
        bottlenecks.append("coding_actions_missing: repo analysis works, but patch/test execution is not yet modeled")
    if probe.probe_id == "idea_memory_synthesis":
        bottlenecks.append("memory_linking_partial: idea capture primitives exist, but workflow interpreter does not yet write/link memories")
    if probe.probe_id == "mobile_approval_notification":
        bottlenecks.append("notification_delivery_external: ntfy exists but live external delivery is policy/environment dependent")
    if probe.probe_id == "social_trend_crawler":
        bottlenecks.append("live_crawler_missing: checked-in feed probe works, production Reddit/DCInside collectors are not implemented")
    if probe.probe_id == "wsj_newsletter_analysis":
        bottlenecks.append("live_gmail_missing: checked-in mail source works, production Gmail OAuth ingestion is not implemented")
    return bottlenecks
