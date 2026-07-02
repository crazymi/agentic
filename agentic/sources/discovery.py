from __future__ import annotations

import json
import sqlite3
import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from agentic.config.settings import AppConfig, load_app_config
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.runtime.worker import TaskExecutionContext
from agentic.sources.models import SourceDefinition, SourceKind, SourcePolicy, utc_now
from agentic.sources.store import SourceStore
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore
from agentic.tasks.subagent_task import SubAgentTask
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel.lifecycle import WorkflowLifecycleService
from agentic.workflow_kernel.store import WorkflowStore
from agentic.scheduler import ScheduleStore
from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.tooling import ToolingBacklogStore


SOURCE_DISCOVERY_TASK_KIND = "source_discovery"


def source_candidate_id() -> str:
    return f"scand_{uuid4().hex}"


class SourceCandidateStatus:
    PROPOSED = "proposed"
    REGISTERED = "registered"
    REJECTED = "rejected"


@dataclass(frozen=True)
class SourceCandidate:
    requested_source: str
    kind: SourceKind
    name: str
    locator: str
    workflow_id: str = ""
    candidate_id: str = field(default_factory=source_candidate_id)
    aliases: list[str] = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    status: str = SourceCandidateStatus.PROPOSED
    source_id: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", SourceKind(self.kind))
        if not self.requested_source:
            raise ValueError("requested_source must not be empty")
        if not self.name:
            raise ValueError("source candidate name must not be empty")
        if not self.locator:
            raise ValueError("source candidate locator must not be empty")
        confidence = max(0.0, min(float(self.confidence), 1.0))
        object.__setattr__(self, "confidence", confidence)

    def to_record(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "workflow_id": self.workflow_id,
            "requested_source": self.requested_source,
            "kind": self.kind.value,
            "name": self.name,
            "locator": self.locator,
            "aliases": self.aliases,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "status": self.status,
            "source_id": self.source_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SourceCandidate":
        return cls(
            candidate_id=str(record["candidate_id"]),
            workflow_id=str(record.get("workflow_id") or ""),
            requested_source=str(record["requested_source"]),
            kind=SourceKind(record["kind"]),
            name=str(record["name"]),
            locator=str(record["locator"]),
            aliases=[str(item) for item in record.get("aliases") or []],
            confidence=float(record.get("confidence") or 0.0),
            rationale=str(record.get("rationale") or ""),
            evidence=[dict(item) for item in record.get("evidence") or [] if isinstance(item, dict)],
            status=str(record.get("status") or SourceCandidateStatus.PROPOSED),
            source_id=str(record.get("source_id") or ""),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )


class SourceCandidateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, candidate: SourceCandidate) -> SourceCandidate:
        with self._connect() as conn:
            conn.execute(
                """
                insert into source_candidates (
                    candidate_id, workflow_id, requested_source, status, locator,
                    record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.workflow_id,
                    candidate.requested_source,
                    candidate.status,
                    candidate.locator,
                    self._dump(candidate.to_record()),
                    candidate.created_at,
                    candidate.updated_at,
                ),
            )
        return candidate

    def get(self, candidate_id: str) -> SourceCandidate:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from source_candidates where candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown source candidate id: {candidate_id}")
        return SourceCandidate.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        workflow_id: str | None = None,
        requested_source: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[SourceCandidate]:
        clauses: list[str] = []
        params: list[Any] = []
        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if requested_source is not None:
            clauses.append("requested_source = ?")
            params.append(requested_source)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from source_candidates{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [SourceCandidate.from_record(json.loads(row["record_json"])) for row in rows]

    def update(self, candidate: SourceCandidate) -> SourceCandidate:
        current = self.get(candidate.candidate_id)
        updated = SourceCandidate.from_record(
            {
                **candidate.to_record(),
                "created_at": current.created_at,
                "updated_at": utc_now(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update source_candidates
                set workflow_id = ?, requested_source = ?, status = ?, locator = ?,
                    record_json = ?, updated_at = ?
                where candidate_id = ?
                """,
                (
                    updated.workflow_id,
                    updated.requested_source,
                    updated.status,
                    updated.locator,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    updated.candidate_id,
                ),
            )
        return updated

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists source_candidates (
                    candidate_id text primary key,
                    workflow_id text not null,
                    requested_source text not null,
                    status text not null,
                    locator text not null,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SourceCandidateService:
    def __init__(
        self,
        *,
        candidate_store: SourceCandidateStore,
        source_store: SourceStore,
    ):
        self.candidate_store = candidate_store
        self.source_store = source_store

    def propose(
        self,
        *,
        requested_source: str,
        kind: SourceKind | str,
        name: str,
        locator: str,
        workflow_id: str = "",
        aliases: list[str] | None = None,
        confidence: float = 0.0,
        rationale: str = "",
        evidence: list[dict[str, Any]] | None = None,
        auto_register: bool = False,
    ) -> dict[str, Any]:
        candidate = self.candidate_store.create(
            SourceCandidate(
                workflow_id=workflow_id,
                requested_source=requested_source,
                kind=SourceKind(kind),
                name=name,
                locator=locator,
                aliases=_dedupe([requested_source, *(aliases or [])]),
                confidence=confidence,
                rationale=rationale,
                evidence=evidence or [],
            )
        )
        source: SourceDefinition | None = None
        if auto_register:
            source = self._register(candidate)
            candidate = self.candidate_store.update(
                SourceCandidate.from_record(
                    {
                        **candidate.to_record(),
                        "status": SourceCandidateStatus.REGISTERED,
                        "source_id": source.source_id,
                    }
                )
            )
        return {
            "ok": True,
            "candidate": candidate.to_record(),
            "source": source.to_record() if source is not None else None,
        }

    def _register(self, candidate: SourceCandidate) -> SourceDefinition:
        if candidate.kind != SourceKind.WEB_PAGE:
            raise ValueError("auto_register currently supports read-only web_page sources only")
        if candidate.confidence < 0.55:
            raise ValueError("auto_register requires candidate confidence >= 0.55")
        parsed = urlparse(candidate.locator)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("auto_register requires an http(s) locator")
        existing = self._find_existing(candidate.locator)
        if existing is not None:
            return existing
        return self.source_store.add_source(
            SourceDefinition(
                kind=SourceKind.WEB_PAGE,
                name=candidate.name,
                locator=candidate.locator,
                enabled=True,
                policy=SourcePolicy(read_only=True, requires_approval=False),
                metadata={
                    "aliases": candidate.aliases,
                    "registered_from": "source_discovery",
                    "source_candidate_id": candidate.candidate_id,
                    "requested_source": candidate.requested_source,
                    "confidence": candidate.confidence,
                    "rationale": candidate.rationale,
                    "evidence": candidate.evidence,
                },
            )
        )

    def _find_existing(self, locator: str) -> SourceDefinition | None:
        for source in self.source_store.list_sources(enabled=True, limit=500):
            if source.locator == locator:
                return source
        return None


class SourceDiscoveryEnqueuer:
    def __init__(
        self,
        *,
        task_store: TaskStore,
        state_dir: str | Path,
        config_path: str = "config/config.toml",
        model_id: str = "",
        model_max_tokens: int = 512,
    ):
        self.task_store = task_store
        self.state_dir = Path(state_dir)
        self.config_path = config_path
        self.model_id = model_id
        self.model_max_tokens = model_max_tokens

    def enqueue(
        self,
        *,
        workflow_id: str,
        user_request: str,
        missing_sources: list[str],
        feedback: str = "",
    ) -> TaskRecord:
        existing = self._find_existing(workflow_id, missing_sources)
        if existing is not None:
            return existing
        return self.task_store.create_task(
            kind=SOURCE_DISCOVERY_TASK_KIND,
            input={
                "state_dir": str(self.state_dir),
                "config_path": self.config_path,
                "model_id": self.model_id,
                "model_max_tokens": self.model_max_tokens,
                "workflow_id": workflow_id,
                "user_request": user_request,
                "missing_sources": missing_sources,
                "feedback": feedback.strip(),
            },
        )

    def _find_existing(self, workflow_id: str, missing_sources: list[str]) -> TaskRecord | None:
        live_statuses = {
            DurableTaskStatus.QUEUED,
            DurableTaskStatus.RUNNING,
            DurableTaskStatus.PAUSED,
            DurableTaskStatus.CANCEL_REQUESTED,
        }
        requested = sorted(str(item) for item in missing_sources)
        for task in self.task_store.list_tasks(kind=SOURCE_DISCOVERY_TASK_KIND, limit=500):
            if task.status not in live_statuses:
                continue
            if str(task.input.get("workflow_id") or "") != workflow_id:
                continue
            if sorted(str(item) for item in task.input.get("missing_sources") or []) == requested:
                return task
        return None


class SourceDiscoveryExecutor:
    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        default_state_dir: str | Path,
    ):
        self.config = config
        self.default_state_dir = Path(default_state_dir)

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict[str, Any]:
        state_dir = Path(task.input.get("state_dir") or self.default_state_dir)
        config = self._config(task)
        model_id = str(task.input.get("model_id") or config.runtime.default_subagent_model)
        max_tokens = int(task.input.get("model_max_tokens") or 512)
        provider = LocalGGUFProvider(config.model(model_id)).with_max_tokens(max_tokens)
        trace = TraceLogger(state_dir / "source_discovery_trace.jsonl")
        from agentic.prompts.builder import PromptBuilder
        from agentic.runtime.subagent_loop import SubagentLoop
        from agentic.tools.registry import ToolRegistry
        from agentic.tools.source_discovery import source_candidate_tool
        from agentic.tools.web_search import WEB_SEARCH_TOOL

        search_loop = SubagentLoop(
            provider=provider,
            prompt_builder=PromptBuilder.from_files(
                config.prompts.master,
                config.prompts.subagent,
                config.prompts.tool_call_grammar,
            ),
            tools=ToolRegistry([WEB_SEARCH_TOOL]),
            trace=trace,
        )
        candidate_loop = SubagentLoop(
            provider=provider,
            prompt_builder=PromptBuilder.from_files(
                config.prompts.master,
                config.prompts.subagent,
                config.prompts.tool_call_grammar,
            ),
            tools=ToolRegistry([source_candidate_tool(state_dir)]),
            trace=trace,
        )
        workflow_id = str(task.input.get("workflow_id") or "")
        user_request = str(task.input.get("user_request") or "")
        missing_sources = [str(item) for item in task.input.get("missing_sources") or [] if str(item)]
        user_feedback = str(task.input.get("feedback") or "").strip()
        context.raise_if_cancelled(task.task_id)
        context.heartbeat(task.task_id)
        search_result = None
        search_reports: list[str] = []
        search_feedback = user_feedback
        for _attempt in range(3):
            search_result = search_loop.run_once(
                SubAgentTask(
                    instruction=_search_instruction(
                        workflow_id=workflow_id,
                        user_request=user_request,
                        missing_sources=missing_sources,
                        feedback=search_feedback,
                    )
                )
            )
            if not search_result.ok:
                break
            search_reports.append(search_result.report or "")
            if _search_report_has_results(search_result.report or ""):
                break
            search_feedback = (
                "The previous web_search returned zero results. "
                "Use the original user-provided source hints and choose a better query. "
                "Do not search for the notification channel unless that is the missing source."
            )
        if search_result is None:
            return {"ok": False, "stage": "search", "error": {"type": "no_search_attempt"}}
        if not search_result.ok:
            return {
                "ok": False,
                "stage": "search",
                "error": {
                    "type": search_result.error_type,
                    "message": search_result.error_message,
                },
            }
        context.raise_if_cancelled(task.task_id)
        context.heartbeat(task.task_id)
        candidate_result = candidate_loop.run_once(
            SubAgentTask(
                instruction=_candidate_instruction(
                    workflow_id=workflow_id,
                    user_request=user_request,
                    missing_sources=missing_sources,
                    search_report=_compact_search_reports(search_reports or [search_result.report or ""]),
                )
            )
        )
        if not candidate_result.ok:
            return {
                "ok": False,
                "stage": "candidate",
                "search_report": "\n\n".join(search_reports) or search_result.report,
                "error": {
                    "type": candidate_result.error_type,
                    "message": candidate_result.error_message,
                },
            }
        context.raise_if_cancelled(task.task_id)
        context.heartbeat(task.task_id)
        lifecycle = build_source_discovery_lifecycle_service(state_dir)
        advance = lifecycle.advance_after_proposal(workflow_id).to_record() if workflow_id else {}
        candidates = SourceCandidateStore(state_dir / "source_candidates.sqlite3").list(
            workflow_id=workflow_id or None,
            limit=20,
        )
        sources = SourceStore(state_dir / "sources.sqlite3").list_sources(enabled=True, limit=20)
        return {
            "ok": bool(advance.get("ok")) if advance else bool(sources),
            "stage": "advanced" if advance else "candidate_created",
            "search_report": search_result.report,
            "candidate_report": candidate_result.report,
            "candidates": [candidate.to_record() for candidate in candidates],
            "sources": [source.to_record() for source in sources],
            "workflow_lifecycle": advance,
        }

    def _config(self, task: TaskRecord) -> AppConfig:
        if self.config is not None:
            return self.config
        config_path = str(task.input.get("config_path") or "config/config.toml")
        return load_app_config(config_path)


def build_source_candidate_service(state_dir: str | Path) -> SourceCandidateService:
    root = Path(state_dir)
    return SourceCandidateService(
        candidate_store=SourceCandidateStore(root / "source_candidates.sqlite3"),
        source_store=SourceStore(root / "sources.sqlite3"),
    )


def build_source_discovery_lifecycle_service(state_dir: str | Path) -> WorkflowLifecycleService:
    root = Path(state_dir)
    return WorkflowLifecycleService(
        workflow_store=WorkflowStore(root / "workflows.sqlite3"),
        source_store=SourceStore(root / "sources.sqlite3"),
        schedule_store=ScheduleStore(root / "schedules.sqlite3"),
        artifact_store=ArtifactStore(root / "artifacts.sqlite3"),
        resource_store=ResourceStore(root / "resources.sqlite3"),
        tooling_store=ToolingBacklogStore(root / "tooling.sqlite3"),
    )


def _search_instruction(
    *,
    workflow_id: str,
    user_request: str,
    missing_sources: list[str],
    feedback: str = "",
) -> str:
    return (
        "You are the source-discovery subagent in a local Harness. "
        "You were not given a URL. Use an allowed tool to discover candidate public sources. "
        "Output exactly one JSON tool call and no commentary. Prefer web_search for unknown public web sources. "
        "Do not set a search provider unless the user explicitly requested one; the runtime will choose an available provider. "
        "Do not invent a URL. Do not register a source yet. "
        f"Runtime feedback: {feedback}. "
        f"Workflow id: {workflow_id}. "
        f"Missing source labels: {missing_sources}. "
        f"Original user request: {user_request}. "
        'Example shape: {"tool":"web_search","arguments":{"query":"official source name or community name","count":5,"language":"ko"}}'
    )


def _search_report_has_results(report: str) -> bool:
    try:
        data = json.loads(report.replace("'", '"'))
    except Exception:
        return "'results': []" not in report and '"results": []' not in report and "'count': 0" not in report
    return bool(data.get("results")) or int(data.get("count") or 0) > 0


def _compact_search_reports(reports: list[str]) -> str:
    compacted: list[dict[str, Any]] = []
    for report in reports:
        data = _parse_report_mapping(report)
        if not data:
            continue
        compacted.append(
            {
                "provider": data.get("provider"),
                "query": data.get("query"),
                "results": [
                    {"title": str(item.get("title") or "")[:100], "url": str(item.get("url") or "")}
                    for item in list(data.get("results") or [])[:3]
                    if isinstance(item, dict)
                ],
            }
        )
    return json.dumps(compacted, ensure_ascii=False)


def _parse_report_mapping(report: str) -> dict[str, Any]:
    try:
        value = ast.literal_eval(report)
    except Exception:
        try:
            value = json.loads(report)
        except Exception:
            return {}
    return dict(value) if isinstance(value, dict) else {}


def _candidate_instruction(
    *,
    workflow_id: str,
    user_request: str,
    missing_sources: list[str],
    search_report: str,
) -> str:
    clipped = search_report[:1200]
    requested_source = missing_sources[0] if missing_sources else "source"
    return (
        "Choose the best public read-only source candidate from the search results. "
        "Call source_candidate exactly once. Output one JSON object only. Do not invent URLs. "
        "Keep the JSON short. Do not include aliases, rationale, or evidence unless explicitly required. "
        f"Workflow id: {workflow_id}. "
        f"Missing source labels: {missing_sources}. "
        f"User source context: {user_request[:500]}. "
        f"Tool result: {clipped}. "
        "Use this compact shape and replace only the locator/name from search results: "
        '{"tool":"source_candidate","arguments":{"action":"create",'
        f'"workflow_id":"{workflow_id}","requested_source":"{requested_source}",'
        '"kind":"web_page","name":"short name","locator":"https://result-url",'
        '"confidence":0.8,"auto_register":true}}'
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result
