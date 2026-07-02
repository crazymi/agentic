from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceRuntime, SourceStore
from agentic.workflow_kernel.interpreter import WorkflowBuilder, WorkflowExecutionResult, WorkflowInterpreter
from agentic.workflow_kernel.models import StepType, WorkflowSpec, WorkflowStatus
from agentic.workflow_kernel.store import WorkflowStore

if TYPE_CHECKING:
    from agentic.scheduler.models import ScheduleRecord
    from agentic.scheduler.store import ScheduleStore
    from agentic.tooling import ToolingBacklogStore


@dataclass(frozen=True)
class WorkflowReviewResult:
    workflow_id: str
    ok: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: int = 0
    review_hash: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "ok": self.ok,
            "failures": self.failures,
            "warnings": self.warnings,
            "score": self.score,
            "review_hash": self.review_hash,
        }


@dataclass(frozen=True)
class SourceBindingResult:
    workflow_id: str
    ok: bool
    bound_sources: list[dict[str, Any]] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "ok": self.ok,
            "bound_sources": self.bound_sources,
            "missing_sources": self.missing_sources,
        }


@dataclass(frozen=True)
class WorkflowLifecycleAdvanceResult:
    workflow_id: str
    ok: bool
    status: str
    review: dict[str, Any] | None = None
    source_binding: dict[str, Any] | None = None
    workflow: dict[str, Any] | None = None
    blockers: list[dict[str, Any]] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "ok": self.ok,
            "status": self.status,
            "review": self.review,
            "source_binding": self.source_binding,
            "workflow": self.workflow,
            "blockers": self.blockers,
        }


class WorkflowLifecycleService:
    def __init__(
        self,
        *,
        workflow_store: WorkflowStore,
        source_store: SourceStore,
        schedule_store: ScheduleStore | None = None,
        artifact_store: ArtifactStore | None = None,
        resource_store: ResourceStore | None = None,
        tooling_store: ToolingBacklogStore | None = None,
        source_recovery_enqueuer: Any | None = None,
        source_discovery_enqueuer: Any | None = None,
        report_synthesizer: Any | None = None,
    ):
        self.workflow_store = workflow_store
        self.source_store = source_store
        self.schedule_store = schedule_store
        self.artifact_store = artifact_store
        self.resource_store = resource_store
        self.tooling_store = tooling_store
        self.source_recovery_enqueuer = source_recovery_enqueuer
        self.source_discovery_enqueuer = source_discovery_enqueuer
        self.report_synthesizer = report_synthesizer

    def review(self, workflow_id: str) -> WorkflowReviewResult:
        spec = self.workflow_store.get_spec(workflow_id)
        result = review_workflow_spec(spec)
        self.workflow_store.update_spec(
            _with_lifecycle(spec, {"last_review": result.to_record()}),
            event_type="workflow_reviewed",
            event_payload=result.to_record(),
        )
        return result

    def bind_sources(self, workflow_id: str) -> SourceBindingResult:
        spec = self.workflow_store.get_spec(workflow_id)
        result, updated = bind_declared_sources(spec, self.source_store)
        event_type = "workflow_sources_bound" if result.ok else "workflow_source_binding_missing"
        event_payload = result.to_record()
        if updated is not None:
            self.workflow_store.update_spec(updated, event_type=event_type, event_payload=event_payload)
        else:
            self.workflow_store.append_event(event_type, event_payload, workflow_id=workflow_id)
        return result

    def approve(self, workflow_id: str) -> WorkflowSpec:
        spec = self.workflow_store.get_spec(workflow_id)
        review = review_workflow_spec(spec)
        if not review.ok:
            self.workflow_store.append_event(
                "workflow_approval_blocked",
                {"reason": "review_failed", "review": review.to_record()},
                workflow_id=workflow_id,
            )
            raise ValueError("workflow review must pass before approval")
        if not _source_binding_ready(spec):
            binding, _ = bind_declared_sources(spec, self.source_store)
            self.workflow_store.append_event(
                "workflow_approval_blocked",
                {"reason": "source_binding_missing", "binding": binding.to_record()},
                workflow_id=workflow_id,
            )
            raise ValueError("workflow sources must be bound before approval")
        return self.workflow_store.transition_spec(
            workflow_id,
            WorkflowStatus.APPROVED,
            event_type="workflow_approved",
            event_payload={"workflow_id": workflow_id, "review_hash": review.review_hash},
        )

    def activate(self, workflow_id: str) -> WorkflowSpec:
        spec = self.workflow_store.get_spec(workflow_id)
        if not _source_binding_ready(spec):
            self.workflow_store.append_event(
                "workflow_activation_blocked",
                {"reason": "source_binding_missing"},
                workflow_id=workflow_id,
            )
            raise ValueError("workflow sources must be bound before activation")
        active = self.workflow_store.transition_spec(
            workflow_id,
            WorkflowStatus.ACTIVE,
            event_type="workflow_activated",
            event_payload={"workflow_id": workflow_id},
        )
        schedules = self._ensure_schedules(active)
        if schedules:
            self.workflow_store.append_event(
                "workflow_schedules_created",
                {"schedule_ids": [schedule.schedule_id for schedule in schedules]},
                workflow_id=workflow_id,
            )
        return active

    def run_once(self, workflow_id: str) -> WorkflowExecutionResult:
        spec = self.workflow_store.get_spec(workflow_id)
        if not _source_binding_ready(spec):
            self.workflow_store.append_event(
                "workflow_run_blocked",
                {"reason": "source_binding_missing"},
                workflow_id=workflow_id,
            )
            raise ValueError("workflow sources must be bound before run")
        if self.artifact_store is None or self.resource_store is None:
            raise ValueError("workflow run requires artifact_store and resource_store")
        interpreter = WorkflowInterpreter(
            workflow_store=self.workflow_store,
            artifact_store=self.artifact_store,
            source_runtime=SourceRuntime(
                source_store=self.source_store,
                resource_store=self.resource_store,
            ),
            resource_store=self.resource_store,
            tooling_store=self.tooling_store,
            source_recovery_enqueuer=self.source_recovery_enqueuer,
            report_synthesizer=self.report_synthesizer,
        )
        return WorkflowBuilder(interpreter).run_approved(spec, trigger={"type": "manual"})

    def advance_after_proposal(
        self,
        workflow_id: str,
        *,
        auto_activate_read_only: bool = True,
    ) -> WorkflowLifecycleAdvanceResult:
        review = self.review(workflow_id)
        spec = self.workflow_store.get_spec(workflow_id)
        blockers: list[dict[str, Any]] = []
        if not review.ok:
            blockers.append({"type": "review_failed", "review": review.to_record()})
            self.workflow_store.append_event(
                "workflow_lifecycle_advance_blocked",
                {"blockers": blockers},
                workflow_id=workflow_id,
            )
            return WorkflowLifecycleAdvanceResult(
                workflow_id=workflow_id,
                ok=False,
                status="blocked",
                review=review.to_record(),
                blockers=blockers,
            )
        binding = self.bind_sources(workflow_id)
        if not binding.ok:
            discovery_task = self._enqueue_source_discovery(spec, binding)
            blocker = {"type": "source_binding_missing", "binding": binding.to_record()}
            if discovery_task is not None:
                blocker["source_discovery_task_id"] = discovery_task.task_id
            blockers.append(blocker)
            self.workflow_store.append_event(
                "workflow_lifecycle_advance_blocked",
                {"blockers": blockers},
                workflow_id=workflow_id,
            )
            return WorkflowLifecycleAdvanceResult(
                workflow_id=workflow_id,
                ok=False,
                status="blocked",
                review=review.to_record(),
                source_binding=binding.to_record(),
                blockers=blockers,
            )
        spec = self.workflow_store.get_spec(workflow_id)
        if spec.status == WorkflowStatus.ACTIVE:
            self.workflow_store.append_event(
                "workflow_lifecycle_advance_already_active",
                {"source_binding": binding.to_record()},
                workflow_id=workflow_id,
            )
            return WorkflowLifecycleAdvanceResult(
                workflow_id=workflow_id,
                ok=True,
                status="active",
                review=review.to_record(),
                source_binding=binding.to_record(),
                workflow=spec.to_record(),
            )
        if not _can_auto_activate(spec, binding, auto_activate_read_only=auto_activate_read_only):
            blockers.append({"type": "approval_required_before_activation"})
            self.workflow_store.append_event(
                "workflow_lifecycle_advance_waiting_for_approval",
                {"blockers": blockers, "binding": binding.to_record()},
                workflow_id=workflow_id,
            )
            return WorkflowLifecycleAdvanceResult(
                workflow_id=workflow_id,
                ok=False,
                status="waiting_for_approval",
                review=review.to_record(),
                source_binding=binding.to_record(),
                workflow=spec.to_record(),
                blockers=blockers,
            )
        approved = self.approve(workflow_id)
        active = self.activate(workflow_id)
        return WorkflowLifecycleAdvanceResult(
            workflow_id=workflow_id,
            ok=True,
            status="active",
            review=review.to_record(),
            source_binding=binding.to_record(),
            workflow=active.to_record(),
        )

    def _enqueue_source_discovery(
        self,
        spec: WorkflowSpec,
        binding: SourceBindingResult,
    ) -> Any | None:
        if self.source_discovery_enqueuer is None or not binding.missing_sources:
            return None
        task = self.source_discovery_enqueuer.enqueue(
            workflow_id=spec.workflow_id,
            user_request=_source_discovery_context(spec),
            missing_sources=binding.missing_sources,
            session_log_id=str((spec.inputs or {}).get("session_log_id") or ""),
        )
        self.workflow_store.append_event(
            "workflow_source_discovery_enqueued",
            {
                "task_id": task.task_id,
                "missing_sources": binding.missing_sources,
            },
            workflow_id=spec.workflow_id,
        )
        return task

    def _ensure_schedules(self, spec: WorkflowSpec) -> list[ScheduleRecord]:
        if self.schedule_store is None:
            return []
        from agentic.scheduler.models import ScheduleRecord

        schedules: list[ScheduleRecord] = []
        for trigger in spec.triggers:
            if str(trigger.get("type") or "") != "interval":
                continue
            schedules.append(
                self.schedule_store.create(
                    ScheduleRecord(
                        workflow_id=spec.workflow_id,
                        trigger=trigger,
                    )
                )
            )
        return schedules


def review_workflow_spec(spec: WorkflowSpec) -> WorkflowReviewResult:
    failures: list[str] = []
    warnings: list[str] = []
    step_types = [step.step_type.value for step in spec.steps]
    for required in (StepType.COLLECT.value, StepType.ANALYZE.value, StepType.REPORT.value):
        if required not in step_types:
            failures.append(f"missing_step:{required}")
    if not spec.triggers:
        failures.append("missing_trigger")
    if not spec.sources:
        failures.append("missing_sources")
    if not spec.outputs:
        failures.append("missing_outputs")
    if not spec.success_criteria:
        failures.append("missing_success_criteria")
    if spec.status not in {
        WorkflowStatus.PROPOSED,
        WorkflowStatus.APPROVED,
        WorkflowStatus.ACTIVE,
        WorkflowStatus.PAUSED,
    }:
        failures.append(f"invalid_review_status:{spec.status.value}")
    if not _source_binding_ready(spec):
        warnings.append("source_binding_missing")
    if any(step.step_type in {StepType.RUN_SCRIPT, StepType.BROWSER_ACTION} for step in spec.steps):
        warnings.append("sensitive_execution_step_requires_policy")
    score = max(0, 100 - len(failures) * 25 - len(warnings) * 10)
    payload = {
        "workflow_id": spec.workflow_id,
        "version": spec.version,
        "status": spec.status.value,
        "step_types": step_types,
        "failures": failures,
        "warnings": warnings,
    }
    digest = hashlib.sha256(
        repr(sorted(payload.items())).encode("utf-8")
    ).hexdigest()
    return WorkflowReviewResult(
        workflow_id=spec.workflow_id,
        ok=not failures,
        failures=failures,
        warnings=warnings,
        score=score,
        review_hash=digest,
    )


def bind_declared_sources(
    spec: WorkflowSpec,
    source_store: SourceStore,
) -> tuple[SourceBindingResult, WorkflowSpec | None]:
    requested_sources = _requested_sources(spec)
    if not requested_sources:
        result = SourceBindingResult(spec.workflow_id, ok=False, missing_sources=["<none>"])
        return result, None
    enabled_sources = source_store.list_sources(enabled=True, limit=500)
    bound: list[dict[str, Any]] = []
    missing: list[str] = []
    for requested in requested_sources:
        match = _match_source(requested, enabled_sources)
        if match is None:
            missing.append(requested)
            continue
        bound.append(_source_binding_record(requested, match))
    if missing:
        return SourceBindingResult(spec.workflow_id, ok=False, bound_sources=bound, missing_sources=missing), None
    record = spec.to_record()
    record["sources"] = bound
    record["inputs"] = {
        **dict(record.get("inputs") or {}),
        "source_ids": [source["source_id"] for source in bound],
        "source_binding_status": "bound",
    }
    record["policy"] = _lifecycle_policy(record, {"source_binding_status": "bound"})
    record["steps"] = _bind_collect_steps(record["steps"], bound)
    updated = WorkflowSpec.from_record(record)
    return SourceBindingResult(spec.workflow_id, ok=True, bound_sources=bound), updated


def _requested_sources(spec: WorkflowSpec) -> list[str]:
    values: list[str] = []
    for source in spec.sources:
        value = (
            source.get("requested")
            or source.get("type")
            or source.get("name")
            or source.get("kind")
            or source.get("connector_id")
            or source.get("source_id")
        )
        if value:
            values.append(str(value))
    if not values:
        source = spec.inputs.get("source")
        if source:
            values.extend(part.strip() for part in str(source).split("+") if part.strip())
    return values


def _match_source(requested: str, sources: list[SourceDefinition]) -> SourceDefinition | None:
    requested_key = requested.strip().lower()
    for source in sources:
        metadata = dict(source.metadata or {})
        aliases = [str(item).lower() for item in metadata.get("aliases", []) if item]
        candidates = {
            source.source_id.lower(),
            source.kind.value.lower(),
            source.name.lower(),
            source.connector_id.lower(),
            str(metadata.get("requested_source") or "").lower(),
            *aliases,
        }
        if requested_key in candidates:
            return source
    return None


def _source_binding_record(requested: str, source: SourceDefinition) -> dict[str, Any]:
    return {
        "requested": requested,
        "source_id": source.source_id,
        "kind": source.kind.value,
        "name": source.name,
        "locator": source.locator,
        "connector_id": source.connector_id,
        "mode": "enabled_source_binding",
    }


def _bind_collect_steps(steps: list[dict[str, Any]], bound: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_ids = [source["source_id"] for source in bound]
    source_kinds = [source["kind"] for source in bound]
    updated_steps: list[dict[str, Any]] = []
    for step in steps:
        if step.get("step_type") != StepType.COLLECT.value:
            updated_steps.append(step)
            continue
        updated_steps.append(
            {
                **step,
                "config": {
                    **dict(step.get("config") or {}),
                    "source_id": source_ids[0],
                    "source_ids": source_ids,
                    "source": source_kinds[0],
                    "sources": source_kinds,
                },
            }
        )
    return updated_steps


def _source_binding_ready(spec: WorkflowSpec) -> bool:
    lifecycle = dict(spec.policy.get("lifecycle") or {})
    if lifecycle.get("source_binding_status") == "bound":
        return True
    if spec.inputs.get("source_binding_status") == "bound":
        return True
    return all(bool(source.get("source_id")) for source in spec.sources) and bool(spec.sources)


def _can_auto_activate(
    spec: WorkflowSpec,
    binding: SourceBindingResult,
    *,
    auto_activate_read_only: bool,
) -> bool:
    if not auto_activate_read_only:
        return False
    policy = dict(spec.policy or {})
    if policy.get("activation_requires_approval"):
        return False
    if str(policy.get("risk") or "low") != "low":
        return False
    for source in binding.bound_sources:
        source_id = str(source.get("source_id") or "")
        if not source_id:
            return False
    return True


def _with_lifecycle(spec: WorkflowSpec, updates: dict[str, Any]) -> WorkflowSpec:
    record = spec.to_record()
    record["policy"] = _lifecycle_policy(record, updates)
    return WorkflowSpec.from_record(record)


def _lifecycle_policy(record: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    policy = dict(record.get("policy") or {})
    lifecycle = {**dict(policy.get("lifecycle") or {}), **updates}
    policy["lifecycle"] = lifecycle
    return policy


def _source_discovery_context(spec: WorkflowSpec) -> str:
    slot_answers = dict((spec.inputs or {}).get("slot_answers") or {})
    lines = [
        f"description: {spec.description}",
        f"goal: {spec.goal}",
        f"source_label: {(spec.inputs or {}).get('source') or ''}",
        f"source_user_answer: {slot_answers.get('source') or ''}",
        f"cadence_user_answer: {slot_answers.get('cadence') or (spec.inputs or {}).get('cadence') or ''}",
        f"output: {(spec.inputs or {}).get('output') or spec.outputs}",
    ]
    return "\n".join(line for line in lines if line.strip())
