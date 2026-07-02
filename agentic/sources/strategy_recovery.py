from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic.artifacts import ArtifactStore
from agentic.config.settings import load_app_config
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.resources.store import ResourceStore
from agentic.runtime.worker import TaskExecutionContext
from agentic.scheduler import ScheduleStore
from agentic.sources.models import SourceDefinition
from agentic.sources.store import SourceStore
from agentic.sources.strategy_workshop import (
    SourceStrategyProposal,
    SourceStrategyProposalStatus,
    SourceStrategyProposalStore,
    SourceStrategyWorkshopService,
)
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore
from agentic.tooling import ToolingBacklogStore, ToolingRequest, ToolingStatus
from agentic.synthesis.report import ModelReportSynthesizer, ReportSynthesizer
from agentic.workflow_kernel.lifecycle import WorkflowLifecycleService
from agentic.workflow_kernel.store import WorkflowStore


SOURCE_STRATEGY_RECOVERY_TASK_KIND = "source_strategy_recovery"


@dataclass(frozen=True)
class SourceStrategyRecoveryResult:
    tooling_id: str
    ok: bool
    status: str
    source_id: str = ""
    workflow_id: str | None = None
    proposal_id: str = ""
    run_id: str = ""
    report_artifact_ids: list[str] = field(default_factory=list)
    quality: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "tooling_id": self.tooling_id,
            "ok": self.ok,
            "status": self.status,
            "source_id": self.source_id,
            "workflow_id": self.workflow_id,
            "proposal_id": self.proposal_id,
            "run_id": self.run_id,
            "report_artifact_ids": self.report_artifact_ids,
            "quality": self.quality,
            "error": self.error,
        }


class SourceStrategyRecoveryService:
    def __init__(
        self,
        *,
        source_store: SourceStore,
        proposal_store: SourceStrategyProposalStore,
        tooling_store: ToolingBacklogStore,
        lifecycle_service: WorkflowLifecycleService | None = None,
    ):
        self.source_store = source_store
        self.proposal_store = proposal_store
        self.tooling_store = tooling_store
        self.lifecycle_service = lifecycle_service
        self.workshop = SourceStrategyWorkshopService(
            source_store=source_store,
            proposal_store=proposal_store,
            tooling_store=tooling_store,
        )

    def recover_pending(
        self,
        *,
        limit: int = 10,
        auto_apply: bool = True,
        rerun: bool = True,
    ) -> list[SourceStrategyRecoveryResult]:
        requests = [
            request
            for request in self.tooling_store.list(status=ToolingStatus.PROPOSED, limit=limit)
            if request.capability == "source:strategy_tuning"
        ]
        return [
            self.recover_tooling(
                request.tooling_id,
                auto_apply=auto_apply,
                rerun=rerun,
            )
            for request in requests
        ]

    def recover_tooling(
        self,
        tooling_id: str,
        *,
        auto_apply: bool = True,
        rerun: bool = True,
    ) -> SourceStrategyRecoveryResult:
        request = self.tooling_store.get(tooling_id)
        if request.capability != "source:strategy_tuning":
            return SourceStrategyRecoveryResult(
                tooling_id=tooling_id,
                ok=False,
                status="unsupported_capability",
                error={"type": "unsupported_capability", "capability": request.capability},
            )
        try:
            proposal = self._proposal_for(request)
            source = self.source_store.get_source(proposal.source_id)
            if not auto_apply:
                return SourceStrategyRecoveryResult(
                    tooling_id=tooling_id,
                    ok=True,
                    status="proposed",
                    source_id=proposal.source_id,
                    workflow_id=proposal.workflow_id,
                    proposal_id=proposal.proposal_id,
                    quality=_quality_from_proposal(proposal),
                )
            if not _can_auto_apply(source, request):
                return SourceStrategyRecoveryResult(
                    tooling_id=tooling_id,
                    ok=False,
                    status="blocked_by_policy",
                    source_id=proposal.source_id,
                    workflow_id=proposal.workflow_id,
                    proposal_id=proposal.proposal_id,
                    quality=_quality_from_proposal(proposal),
                    error={"type": "approval_required", "message": "source strategy patch is not safe to auto-apply"},
                )
            if proposal.status == SourceStrategyProposalStatus.PENDING:
                proposal = self.workshop.apply(proposal.proposal_id)
            if not rerun:
                return SourceStrategyRecoveryResult(
                    tooling_id=tooling_id,
                    ok=True,
                    status="applied",
                    source_id=proposal.source_id,
                    workflow_id=proposal.workflow_id,
                    proposal_id=proposal.proposal_id,
                    quality=_quality_from_proposal(proposal),
                )
            if not proposal.workflow_id or self.lifecycle_service is None:
                return SourceStrategyRecoveryResult(
                    tooling_id=tooling_id,
                    ok=True,
                    status="applied_no_rerun",
                    source_id=proposal.source_id,
                    workflow_id=proposal.workflow_id,
                    proposal_id=proposal.proposal_id,
                    quality=_quality_from_proposal(proposal),
                )
            run_result = self.lifecycle_service.run_once(proposal.workflow_id)
            run = run_result.run
            quality = list((run.step_results.get("collect") or {}).get("quality") or [])
            report_artifact_ids = [
                artifact_id
                for artifact_id in run.artifacts
                if isinstance(artifact_id, str)
            ]
            if run_result.ok:
                self.tooling_store.transition(tooling_id, ToolingStatus.COMPLETED)
            return SourceStrategyRecoveryResult(
                tooling_id=tooling_id,
                ok=run_result.ok,
                status="recovered" if run_result.ok else "rerun_failed",
                source_id=proposal.source_id,
                workflow_id=proposal.workflow_id,
                proposal_id=proposal.proposal_id,
                run_id=run.run_id,
                report_artifact_ids=report_artifact_ids,
                quality=quality or _quality_from_proposal(proposal),
                error=run.error,
            )
        except Exception as exc:
            return SourceStrategyRecoveryResult(
                tooling_id=tooling_id,
                ok=False,
                status="failed",
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )

    def _proposal_for(self, request: ToolingRequest) -> SourceStrategyProposal:
        existing = self.proposal_store.find_by_tooling(
            request.tooling_id,
            status=SourceStrategyProposalStatus.PENDING,
        )
        if existing is not None:
            return existing
        applied = self.proposal_store.find_by_tooling(
            request.tooling_id,
            status=SourceStrategyProposalStatus.APPLIED,
        )
        if applied is not None:
            return applied
        return self.workshop.propose_from_tooling(request.tooling_id)


class SourceStrategyRecoveryExecutor:
    def __init__(self, *, default_state_dir: str | Path):
        self.default_state_dir = Path(default_state_dir)

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict[str, Any]:
        state_dir = Path(task.input.get("state_dir") or self.default_state_dir)
        service = build_source_strategy_recovery_service(
            state_dir,
            report_synthesizer=_report_synthesizer_from_task(task),
        )
        context.raise_if_cancelled(task.task_id)
        context.heartbeat(task.task_id)
        tooling_id = str(task.input.get("tooling_id") or "")
        auto_apply = bool(task.input.get("auto_apply", True))
        rerun = bool(task.input.get("rerun", True))
        if tooling_id:
            results = [
                service.recover_tooling(
                    tooling_id,
                    auto_apply=auto_apply,
                    rerun=rerun,
                )
            ]
        else:
            results = service.recover_pending(
                limit=int(task.input.get("limit") or 10),
                auto_apply=auto_apply,
                rerun=rerun,
            )
        context.raise_if_cancelled(task.task_id)
        context.heartbeat(task.task_id)
        return {
            "ok": all(result.ok for result in results),
            "results": [result.to_record() for result in results],
        }


class SourceStrategyRecoveryEnqueuer:
    def __init__(
        self,
        *,
        task_store: TaskStore,
        state_dir: str | Path,
        auto_apply: bool = True,
        rerun: bool = True,
        report_synthesis_model_id: str = "",
        report_synthesis_config_path: str = "",
        report_synthesis_max_tokens: int = 0,
    ):
        self.task_store = task_store
        self.state_dir = Path(state_dir)
        self.auto_apply = auto_apply
        self.rerun = rerun
        self.report_synthesis_model_id = report_synthesis_model_id
        self.report_synthesis_config_path = report_synthesis_config_path
        self.report_synthesis_max_tokens = report_synthesis_max_tokens

    def enqueue(self, request: ToolingRequest) -> TaskRecord:
        existing = self._find_existing(request.tooling_id)
        if existing is not None:
            return existing
        return self.task_store.create_task(
            kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND,
            input={
                "state_dir": str(self.state_dir),
                "tooling_id": request.tooling_id,
                "auto_apply": self.auto_apply,
                "rerun": self.rerun,
                "report_synthesis_model_id": self.report_synthesis_model_id,
                "report_synthesis_config_path": self.report_synthesis_config_path,
                "report_synthesis_max_tokens": self.report_synthesis_max_tokens,
            },
        )

    def _find_existing(self, tooling_id: str) -> TaskRecord | None:
        live_or_done = {
            DurableTaskStatus.QUEUED,
            DurableTaskStatus.RUNNING,
            DurableTaskStatus.PAUSED,
            DurableTaskStatus.CANCEL_REQUESTED,
            DurableTaskStatus.COMPLETED,
        }
        for task in self.task_store.list_tasks(kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND, limit=500):
            if str(task.input.get("tooling_id") or "") != tooling_id:
                continue
            if task.status in live_or_done:
                return task
        return None


def build_source_strategy_recovery_service(
    state_dir: str | Path,
    *,
    report_synthesizer: ReportSynthesizer | None = None,
) -> SourceStrategyRecoveryService:
    root = Path(state_dir)
    source_store = SourceStore(root / "sources.sqlite3")
    tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
    proposal_store = SourceStrategyProposalStore(root / "source_strategy.sqlite3")
    workflow_store = WorkflowStore(root / "workflows.sqlite3")
    lifecycle_service = WorkflowLifecycleService(
        workflow_store=workflow_store,
        source_store=source_store,
        schedule_store=ScheduleStore(root / "schedules.sqlite3"),
        artifact_store=ArtifactStore(root / "artifacts.sqlite3"),
        resource_store=ResourceStore(root / "resources.sqlite3"),
        tooling_store=tooling_store,
        report_synthesizer=report_synthesizer,
    )
    return SourceStrategyRecoveryService(
        source_store=source_store,
        proposal_store=proposal_store,
        tooling_store=tooling_store,
        lifecycle_service=lifecycle_service,
    )


def _can_auto_apply(source: SourceDefinition, request: ToolingRequest) -> bool:
    if request.payload.get("approval_required_before_activation"):
        return False
    if source.credential_ref:
        return False
    if not source.policy.read_only or source.policy.requires_approval:
        return False
    return True


def _quality_from_proposal(proposal: SourceStrategyProposal) -> list[dict[str, Any]]:
    return list(proposal.quality_reports)


def _report_synthesizer_from_task(task: TaskRecord) -> ReportSynthesizer | None:
    model_id = str(task.input.get("report_synthesis_model_id") or "")
    if not model_id:
        return None
    config_path = str(task.input.get("report_synthesis_config_path") or "config/config.toml")
    config = load_app_config(config_path)
    model = config.model(model_id)
    max_tokens = int(task.input.get("report_synthesis_max_tokens") or 0)
    provider = LocalGGUFProvider(model).with_max_tokens(max_tokens) if max_tokens > 0 else LocalGGUFProvider(model)
    return ModelReportSynthesizer(provider)
