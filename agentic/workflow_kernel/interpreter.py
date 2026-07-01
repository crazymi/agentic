from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.artifacts import ArtifactKind, ArtifactRecord, ArtifactStore
from agentic.resources.store import ResourceRecord, ResourceStore
from agentic.sources.runtime import SourceRuntime
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel.capabilities import (
    CapabilityAdmission,
    CapabilityPlanner,
)
from agentic.workflow_kernel.models import (
    StepType,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowSpec,
)
from agentic.workflow_kernel.store import WorkflowStore


@dataclass(frozen=True)
class WorkflowExecutionResult:
    run: WorkflowRun
    ok: bool


class WorkflowInterpreter:
    def __init__(
        self,
        *,
        workflow_store: WorkflowStore,
        artifact_store: ArtifactStore,
        source_runtime: SourceRuntime | None = None,
        resource_store: ResourceStore | None = None,
        capability_planner: CapabilityPlanner | None = None,
        trace: TraceLogger | None = None,
    ):
        self.workflow_store = workflow_store
        self.artifact_store = artifact_store
        self.source_runtime = source_runtime
        self.resource_store = resource_store
        self.capability_planner = capability_planner or CapabilityPlanner()
        self.trace = trace

    def run(self, spec: WorkflowSpec, *, trigger: dict[str, Any] | None = None) -> WorkflowExecutionResult:
        capability_plan = self.capability_planner.plan(spec)
        blocking_need = next(
            (
                need
                for need in capability_plan.needs
                if need.admission
                in {
                    CapabilityAdmission.DENIED,
                    CapabilityAdmission.MISSING,
                    CapabilityAdmission.NEEDS_ARTIFACT_REVIEW,
                }
            ),
            None,
        )
        run = self.workflow_store.create_run(
            spec,
            trigger=trigger or {"type": "manual"},
            context={"capability_plan": capability_plan.to_record()},
        )
        self._trace("workflow_started", {"workflow_id": spec.workflow_id, "run_id": run.run_id})
        if blocking_need is not None:
            updated = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.WAITING_FOR_APPROVAL
                if blocking_need.admission == CapabilityAdmission.NEEDS_ARTIFACT_REVIEW
                else WorkflowRunStatus.FAILED,
                error={
                    "type": "capability_blocked",
                    "need": blocking_need.to_record(),
                },
                event_type="workflow_capability_blocked",
            )
            return WorkflowExecutionResult(run=updated, ok=False)
        if capability_plan.requires_approval:
            updated = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.WAITING_FOR_APPROVAL,
                error={"type": "approval_required", "plan": capability_plan.to_record()},
                event_type="workflow_waiting_for_approval",
            )
            return WorkflowExecutionResult(run=updated, ok=False)

        run = self.workflow_store.transition_run(run.run_id, WorkflowRunStatus.RUNNING)
        context = dict(run.context)
        step_results = dict(run.step_results)
        artifacts = list(run.artifacts)
        try:
            for step in spec.steps:
                self._trace(
                    "workflow_step_started",
                    {"workflow_id": spec.workflow_id, "run_id": run.run_id, "step_id": step.step_id},
                )
                result = self._execute_step(spec, run, step.step_type, step.config, context, step_results)
                step_results[step.step_id] = result
                if "artifact_id" in result:
                    artifacts.append(str(result["artifact_id"]))
                context[step.step_id] = result
                self.workflow_store.append_event(
                    "workflow_step_completed",
                    {"step_id": step.step_id, "result": result},
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                )
                self._trace(
                    "workflow_step_completed",
                    {"workflow_id": spec.workflow_id, "run_id": run.run_id, "step_id": step.step_id},
                )
            run = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.COMPLETED,
                context=context,
                step_results=step_results,
                artifacts=artifacts,
                result={"status": "completed", "artifact_ids": artifacts},
                event_type="workflow_completed",
            )
            self._trace("workflow_completed", {"workflow_id": spec.workflow_id, "run_id": run.run_id})
            return WorkflowExecutionResult(run=run, ok=True)
        except Exception as exc:
            failed = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.FAILED,
                context=context,
                step_results=step_results,
                artifacts=artifacts,
                error={"type": exc.__class__.__name__, "message": str(exc)},
                event_type="workflow_failed",
            )
            self._trace(
                "workflow_failed",
                {"workflow_id": spec.workflow_id, "run_id": run.run_id, "error": str(exc)},
            )
            return WorkflowExecutionResult(run=failed, ok=False)

    def _execute_step(
        self,
        spec: WorkflowSpec,
        run: WorkflowRun,
        step_type: StepType,
        config: dict[str, Any],
        context: dict[str, Any],
        step_results: dict[str, Any],
    ) -> dict[str, Any]:
        if step_type == StepType.COLLECT:
            if self.source_runtime is None or self.resource_store is None:
                raise RuntimeError("collect step requires SourceRuntime and ResourceStore")
            source_id = str(config.get("source_id") or "")
            if not source_id:
                raise RuntimeError("collect step requires source_id")
            collection = self.source_runtime.collect(source_id)
            resources = [self.resource_store.get(resource_id) for resource_id in collection.resource_ids]
            return {
                "items": [_resource_to_item(resource) for resource in resources],
                "source_id": source_id,
                "collected_count": collection.collected_count,
                "new_count": collection.new_count,
                "resource_ids": collection.resource_ids,
            }
        if step_type == StepType.TRANSFORM:
            return {"transformed": True, "input_keys": sorted(step_results.keys())}
        if step_type == StepType.ANALYZE:
            collected = self._first_items(step_results)
            return {
                "summary": f"Analyzed {len(collected)} item(s) for goal: {config.get('goal') or spec.goal}",
                "signals": [item.get("title", "untitled") for item in collected],
            }
        if step_type == StepType.AGGREGATE:
            collected = self._first_items(step_results)
            words: dict[str, int] = {}
            for item in collected:
                for word in str(item.get("text") or item.get("title") or "").split():
                    words[word.lower()] = words.get(word.lower(), 0) + 1
            return {"keyword_counts": words}
        if step_type == StepType.REPORT:
            report = self._render_report(spec, step_results)
            artifact = self.artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name=f"{spec.name} report",
                    content=report,
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                    metadata={"output": config.get("output", "report")},
                )
            )
            return {"artifact_id": artifact.artifact_id, "content": report}
        if step_type == StepType.NOTIFY:
            return {"notified": True, "channel": config.get("channel", "web")}
        if step_type == StepType.ASK_USER:
            raise RuntimeError("ask_user step requires interactive runtime support")
        if step_type == StepType.APPROVAL:
            raise RuntimeError("approval step requires approval service integration")
        if step_type == StepType.RUN_SCRIPT:
            raise RuntimeError("run_script step requires artifact admission")
        return {"ok": True, "step_type": step_type.value}

    @staticmethod
    def _first_items(step_results: dict[str, Any]) -> list[dict[str, Any]]:
        for result in step_results.values():
            items = result.get("items") if isinstance(result, dict) else None
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    @staticmethod
    def _render_report(spec: WorkflowSpec, step_results: dict[str, Any]) -> str:
        analyze = next(
            (
                result
                for result in step_results.values()
                if isinstance(result, dict) and "summary" in result
            ),
            {},
        )
        return "\n".join(
            [
                f"# {spec.name}",
                "",
                f"Goal: {spec.goal}",
                "",
                str(analyze.get("summary") or "No analysis summary."),
            ]
        )

    def _trace(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.trace is not None:
            self.trace.record(event_type, payload)


class WorkflowBuilder:
    def __init__(self, interpreter: WorkflowInterpreter):
        self.interpreter = interpreter

    def run_approved(self, spec: WorkflowSpec, *, trigger: dict[str, Any] | None = None) -> WorkflowExecutionResult:
        if spec.status.value not in {"approved", "active"}:
            raise ValueError("workflow must be approved or active before execution")
        return self.interpreter.run(spec, trigger=trigger)


def _resource_to_item(resource: ResourceRecord) -> dict[str, Any]:
    return {
        "id": resource.resource_id,
        "uri": resource.uri,
        "title": resource.title,
        "text": resource.content_text,
        "metadata": resource.metadata,
    }
