from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from agentic.approvals.service import ApprovalService
from agentic.artifacts import ArtifactStatus, ArtifactStore
from agentic.runtime.task_pool import TaskPool
from agentic.sources import SourceKind, SourceStore
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore
from agentic.workflow_kernel import WorkflowRunStatus, WorkflowStatus, WorkflowStore


class RuntimeHealthStatus:
    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    generated_at: str
    pid: int
    uptime_seconds: float | None
    components: dict[str, dict[str, Any]]
    counters: dict[str, Any]
    recent_failures: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "generated_at": self.generated_at,
            "pid": self.pid,
            "uptime_seconds": self.uptime_seconds,
            "components": self.components,
            "counters": self.counters,
            "recent_failures": self.recent_failures,
            "warnings": self.warnings,
        }


class HealthMonitor:
    def __init__(
        self,
        *,
        task_store: TaskStore | None = None,
        task_pool: TaskPool | None = None,
        workflow_store: WorkflowStore | None = None,
        source_store: SourceStore | None = None,
        artifact_store: ArtifactStore | None = None,
        approvals: ApprovalService | None = None,
        started_at: str | None = None,
    ):
        self.task_store = task_store
        self.task_pool = task_pool
        self.workflow_store = workflow_store
        self.source_store = source_store
        self.artifact_store = artifact_store
        self.approvals = approvals
        self.started_at = started_at or utc_now()

    def snapshot(self) -> HealthSnapshot:
        generated_at = utc_now()
        components: dict[str, dict[str, Any]] = {}
        counters: dict[str, Any] = {}
        warnings: list[str] = []
        recent_failures: list[dict[str, Any]] = []

        task_component, task_counts, task_failures = self._task_health()
        components["tasks"] = task_component
        counters["tasks"] = task_counts
        recent_failures.extend(task_failures)

        workflow_component, workflow_counts, workflow_failures = self._workflow_health()
        components["workflows"] = workflow_component
        counters["workflows"] = workflow_counts
        recent_failures.extend(workflow_failures)

        source_component, source_counts, source_warnings = self._source_health()
        components["sources"] = source_component
        counters["sources"] = source_counts
        warnings.extend(source_warnings)

        artifact_component, artifact_counts = self._artifact_health()
        components["artifacts"] = artifact_component
        counters["artifacts"] = artifact_counts

        approval_component, approval_counts = self._approval_health()
        components["approvals"] = approval_component
        counters["approvals"] = approval_counts
        if approval_counts.get("pending", 0):
            warnings.append(f"{approval_counts['pending']} approval request(s) pending")

        pool_component = self._pool_health()
        components["task_pool"] = pool_component

        status = _overall_status(components, warnings)
        return HealthSnapshot(
            status=status,
            generated_at=generated_at,
            pid=os.getpid(),
            uptime_seconds=_seconds_between(self.started_at, generated_at),
            components=components,
            counters=counters,
            recent_failures=recent_failures[:20],
            warnings=warnings,
        )

    def export_snapshot(self, path: str | Path) -> HealthSnapshot:
        snapshot = self.snapshot()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(snapshot.to_record(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return snapshot

    def _task_health(self) -> tuple[dict[str, Any], dict[str, int], list[dict[str, Any]]]:
        if self.task_store is None:
            return _missing_component("task store not configured"), {}, []
        tasks = self.task_store.list_tasks(limit=1000)
        counts = _count_by_status(task.status.value for task in tasks)
        failures = [
            {
                "type": "task",
                "id": task.task_id,
                "status": task.status.value,
                "kind": task.kind,
                "error": task.error,
                "updated_at": task.updated_at,
            }
            for task in tasks
            if task.status in {DurableTaskStatus.FAILED, DurableTaskStatus.UNHEALTHY}
        ][:10]
        status = RuntimeHealthStatus.UNHEALTHY if counts.get(DurableTaskStatus.UNHEALTHY.value, 0) else RuntimeHealthStatus.OK
        if status == RuntimeHealthStatus.OK and counts.get(DurableTaskStatus.FAILED.value, 0):
            status = RuntimeHealthStatus.DEGRADED
        return {"status": status, "total": len(tasks)}, counts, failures

    def _workflow_health(self) -> tuple[dict[str, Any], dict[str, dict[str, int]], list[dict[str, Any]]]:
        if self.workflow_store is None:
            return _missing_component("workflow store not configured"), {"specs": {}, "runs": {}}, []
        specs = self.workflow_store.list_specs(limit=1000)
        runs = self.workflow_store.list_runs(limit=1000)
        spec_counts = _count_by_status(spec.status.value for spec in specs)
        run_counts = _count_by_status(run.status.value for run in runs)
        failures = [
            {
                "type": "workflow_run",
                "id": run.run_id,
                "workflow_id": run.workflow_id,
                "status": run.status.value,
                "error": run.error,
                "updated_at": run.updated_at,
            }
            for run in runs
            if run.status in {WorkflowRunStatus.FAILED, WorkflowRunStatus.UNHEALTHY}
        ][:10]
        status = RuntimeHealthStatus.OK
        if spec_counts.get(WorkflowStatus.UNHEALTHY.value, 0) or run_counts.get(WorkflowRunStatus.UNHEALTHY.value, 0):
            status = RuntimeHealthStatus.UNHEALTHY
        elif run_counts.get(WorkflowRunStatus.FAILED.value, 0):
            status = RuntimeHealthStatus.DEGRADED
        return (
            {"status": status, "spec_total": len(specs), "run_total": len(runs)},
            {"specs": spec_counts, "runs": run_counts},
            failures,
        )

    def _source_health(self) -> tuple[dict[str, Any], dict[str, int], list[str]]:
        if self.source_store is None:
            return _missing_component("source store not configured"), {}, []
        sources = self.source_store.list_sources(limit=1000)
        enabled = [source for source in sources if source.enabled]
        warnings: list[str] = []
        for source in enabled:
            if source.kind in {SourceKind.LOCAL_FILE, SourceKind.MAIL, SourceKind.FEED, SourceKind.BROWSER_PAGE}:
                path = _locator_to_path(source.locator)
                if not path.exists():
                    warnings.append(f"enabled source missing file: {source.name} -> {path}")
            if source.kind == SourceKind.REPO_STATE:
                path = _locator_to_path(source.locator)
                if not path.exists() or not path.is_dir():
                    warnings.append(f"enabled repo source missing directory: {source.name} -> {path}")
        counts = {
            "total": len(sources),
            "enabled": len(enabled),
            "disabled": len(sources) - len(enabled),
        }
        status = RuntimeHealthStatus.UNHEALTHY if warnings else RuntimeHealthStatus.OK
        return {"status": status, **counts}, counts, warnings

    def _artifact_health(self) -> tuple[dict[str, Any], dict[str, int]]:
        if self.artifact_store is None:
            return _missing_component("artifact store not configured"), {}
        artifacts = self.artifact_store.list(limit=1000)
        counts = _count_by_status(artifact.status.value for artifact in artifacts)
        status = RuntimeHealthStatus.DEGRADED if counts.get(ArtifactStatus.REVIEW_REQUIRED.value, 0) else RuntimeHealthStatus.OK
        return {"status": status, "total": len(artifacts)}, counts

    def _approval_health(self) -> tuple[dict[str, Any], dict[str, int]]:
        if self.approvals is None:
            return _missing_component("approval service not configured"), {}
        pending = self.approvals.get_pending()
        counts = {"pending": len(pending)}
        status = RuntimeHealthStatus.DEGRADED if pending else RuntimeHealthStatus.OK
        return {"status": status, "pending": len(pending)}, counts

    def _pool_health(self) -> dict[str, Any]:
        if self.task_pool is None:
            return _missing_component("task pool not configured")
        return {
            "status": RuntimeHealthStatus.OK,
            "max_workers": self.task_pool.max_workers,
            "running": self.task_pool.running_count(),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_by_status(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _missing_component(reason: str) -> dict[str, Any]:
    return {"status": RuntimeHealthStatus.DEGRADED, "reason": reason}


def _overall_status(components: dict[str, dict[str, Any]], warnings: list[str]) -> str:
    statuses = {str(component.get("status")) for component in components.values()}
    if RuntimeHealthStatus.UNHEALTHY in statuses:
        return RuntimeHealthStatus.UNHEALTHY
    if RuntimeHealthStatus.DEGRADED in statuses or warnings:
        return RuntimeHealthStatus.DEGRADED
    return RuntimeHealthStatus.OK


def _seconds_between(start: str | None, end: str) -> float | None:
    if not start:
        return None
    try:
        started = datetime.fromisoformat(start)
        finished = datetime.fromisoformat(end)
    except ValueError:
        return None
    return max(0.0, (finished - started).total_seconds())


def _locator_to_path(locator: str) -> Path:
    parsed = urlparse(locator)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).expanduser().resolve()
    return Path(locator).expanduser().resolve()
