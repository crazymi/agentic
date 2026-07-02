from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic.tools.base import ToolSpec
from agentic.workflow_kernel import (
    IntentType,
    StepType,
    WorkflowSpec,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStore,
)


DEFAULT_WORKFLOW_DB = Path("traces/state/workflows.sqlite3")


def workflow_spec_tool(store_path: str | Path = DEFAULT_WORKFLOW_DB) -> ToolSpec:
    store = WorkflowStore(store_path)

    def _workflow_spec(
        action: str,
        name: str = "",
        goal: str = "",
        description: str = "",
        steps: list[dict[str, Any]] | None = None,
        step_types: list[str] | None = None,
        triggers: list[dict[str, Any]] | None = None,
        trigger: str = "",
        sources: list[dict[str, Any]] | None = None,
        source: str = "",
        outputs: list[dict[str, Any]] | None = None,
        output: str = "",
        success_criteria: list[str] | None = None,
        assumptions: list[str] | None = None,
        capabilities: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        evals: list[dict[str, Any]] | None = None,
        workflow_id: str = "",
        status: str = "",
        limit: int = 20,
        owner_channel: str = "web",
        intent_type: str = "scheduled_workflow",
    ) -> dict[str, Any]:
        if action == "create":
            spec = WorkflowSpec(
                name=name,
                description=description,
                goal=goal,
                status=WorkflowStatus.PROPOSED,
                intent_type=IntentType(intent_type),
                steps=_normalize_steps(steps or [], step_types=step_types or []),
                triggers=_normalize_triggers(triggers or [], trigger),
                sources=_normalize_sources(sources or [], source),
                outputs=_normalize_outputs(outputs or [], output),
                success_criteria=_normalize_success_criteria(success_criteria or []),
                assumptions=[str(item) for item in (assumptions or [])],
                capabilities=list(capabilities or []),
                policy=dict(policy or {}),
                inputs=dict(inputs or {}),
                evals=list(evals or []),
                owner_channel=owner_channel or "web",
            )
            return {"ok": True, "workflow": store.create_spec(spec).to_record()}
        if action == "inspect":
            return {"ok": True, "workflow": store.get_spec(workflow_id).to_record()}
        if action == "list":
            selected_status = status or None
            workflows = store.list_specs(status=selected_status, limit=limit)
            return {"ok": True, "workflows": [workflow.to_record() for workflow in workflows]}
        raise ValueError(f"unsupported workflow_spec action: {action}")

    return ToolSpec(
        name="workflow_spec",
        description=(
            "Create and inspect pending WorkflowSpec records for review. "
            "This tool never executes, approves, or activates workflows."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "inspect", "list"]},
                "name": {"type": "string"},
                "goal": {"type": "string"},
                "description": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "object"}},
                "step_types": {"type": "array", "items": {"type": "string"}},
                "triggers": {"type": "array", "items": {"type": "object"}},
                "trigger": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "object"}},
                "source": {"type": "string"},
                "outputs": {"type": "array", "items": {"type": "object"}},
                "output": {"type": "string"},
                "success_criteria": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "capabilities": {"type": "array", "items": {"type": "object"}},
                "policy": {"type": "object"},
                "inputs": {"type": "object"},
                "evals": {"type": "array", "items": {"type": "object"}},
                "workflow_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
                "owner_channel": {"type": "string"},
                "intent_type": {"type": "string"},
            },
            "required": ["action"],
        },
        fn=_workflow_spec,
    )


def _normalize_steps(raw_steps: list[dict[str, Any]], *, step_types: list[str]) -> list[WorkflowStep]:
    steps: list[WorkflowStep] = []
    if not raw_steps and step_types:
        raw_steps = [
            {"step_type": step_type, "name": step_type.replace("_", " ").title()}
            for step_type in step_types
        ]
    for index, item in enumerate(raw_steps, start=1):
        step_type = str(item.get("step_type") or item.get("type") or "").strip()
        if not step_type:
            raise ValueError("workflow step requires step_type")
        steps.append(
            WorkflowStep(
                step_id=str(item.get("step_id") or f"step_{index}"),
                step_type=StepType(step_type),
                name=str(item.get("name") or step_type.replace("_", " ").title()),
                config=dict(item.get("config") or {}),
                depends_on=[str(dep) for dep in item.get("depends_on", [])],
            )
        )
    return steps


def _normalize_triggers(raw_triggers: list[dict[str, Any]], trigger: str) -> list[dict[str, Any]]:
    if raw_triggers:
        return raw_triggers
    if trigger:
        return [{"type": "interval" if trigger.startswith("interval:") else "manual", "value": trigger}]
    return [{"type": "manual"}]


def _normalize_sources(raw_sources: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    if raw_sources:
        return raw_sources
    if source:
        return [{"kind": item.strip()} for item in source.split("+") if item.strip()]
    return [{"kind": "selected_source"}]


def _normalize_outputs(raw_outputs: list[dict[str, Any]], output: str) -> list[dict[str, Any]]:
    if raw_outputs:
        return raw_outputs
    if output:
        return [{"kind": output}]
    return [{"kind": "report"}]


def _normalize_success_criteria(raw_criteria: list[str]) -> list[str]:
    if raw_criteria:
        return [str(item) for item in raw_criteria]
    return ["A reviewable workflow output is produced."]
