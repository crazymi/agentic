from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workflow_id() -> str:
    return f"wf_{uuid4().hex}"


def workflow_run_id() -> str:
    return f"wfr_{uuid4().hex}"


def design_session_id() -> str:
    return f"wfd_{uuid4().hex}"


class IntentType(StrEnum):
    ANSWER_NOW = "answer_now"
    ONE_OFF_TASK = "one_off_task"
    DEEP_RESEARCH = "deep_research"
    WORKFLOW_DESIGN = "workflow_design"
    SCHEDULED_WORKFLOW = "scheduled_workflow"
    WATCHER_WORKFLOW = "watcher_workflow"
    CODING_WORKFLOW = "coding_workflow"
    UNKNOWN = "unknown"


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"
    REJECTED = "rejected"
    UNHEALTHY = "unhealthy"


class WorkflowRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNHEALTHY = "unhealthy"


class StepType(StrEnum):
    COLLECT = "collect"
    DEDUPE = "dedupe"
    TRANSFORM = "transform"
    ANALYZE = "analyze"
    AGGREGATE = "aggregate"
    ASK_USER = "ask_user"
    APPROVAL = "approval"
    CALL_TOOL = "call_tool"
    CALL_CONNECTOR = "call_connector"
    RUN_SCRIPT = "run_script"
    REPORT = "report"
    NOTIFY = "notify"
    SUBWORKFLOW = "subworkflow"


ALLOWED_WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    WorkflowStatus.DRAFT: {WorkflowStatus.PROPOSED, WorkflowStatus.REJECTED},
    WorkflowStatus.PROPOSED: {
        WorkflowStatus.APPROVED,
        WorkflowStatus.REJECTED,
        WorkflowStatus.DRAFT,
    },
    WorkflowStatus.APPROVED: {
        WorkflowStatus.ACTIVE,
        WorkflowStatus.PAUSED,
        WorkflowStatus.RETIRED,
    },
    WorkflowStatus.ACTIVE: {
        WorkflowStatus.PAUSED,
        WorkflowStatus.RETIRED,
        WorkflowStatus.UNHEALTHY,
    },
    WorkflowStatus.PAUSED: {
        WorkflowStatus.ACTIVE,
        WorkflowStatus.RETIRED,
        WorkflowStatus.UNHEALTHY,
    },
    WorkflowStatus.UNHEALTHY: {WorkflowStatus.PAUSED, WorkflowStatus.RETIRED},
    WorkflowStatus.REJECTED: set(),
    WorkflowStatus.RETIRED: set(),
}


ALLOWED_RUN_TRANSITIONS: dict[WorkflowRunStatus, set[WorkflowRunStatus]] = {
    WorkflowRunStatus.QUEUED: {
        WorkflowRunStatus.RUNNING,
        WorkflowRunStatus.WAITING_FOR_INPUT,
        WorkflowRunStatus.WAITING_FOR_APPROVAL,
        WorkflowRunStatus.CANCELLED,
        WorkflowRunStatus.FAILED,
    },
    WorkflowRunStatus.RUNNING: {
        WorkflowRunStatus.WAITING_FOR_INPUT,
        WorkflowRunStatus.WAITING_FOR_APPROVAL,
        WorkflowRunStatus.COMPLETED,
        WorkflowRunStatus.FAILED,
        WorkflowRunStatus.CANCELLED,
        WorkflowRunStatus.UNHEALTHY,
    },
    WorkflowRunStatus.WAITING_FOR_INPUT: {
        WorkflowRunStatus.RUNNING,
        WorkflowRunStatus.CANCELLED,
        WorkflowRunStatus.FAILED,
    },
    WorkflowRunStatus.WAITING_FOR_APPROVAL: {
        WorkflowRunStatus.RUNNING,
        WorkflowRunStatus.CANCELLED,
        WorkflowRunStatus.FAILED,
    },
    WorkflowRunStatus.COMPLETED: set(),
    WorkflowRunStatus.FAILED: set(),
    WorkflowRunStatus.CANCELLED: set(),
    WorkflowRunStatus.UNHEALTHY: set(),
}


def assert_workflow_transition(current: WorkflowStatus, next_status: WorkflowStatus) -> None:
    if current == next_status:
        return
    if next_status not in ALLOWED_WORKFLOW_TRANSITIONS[current]:
        raise ValueError(f"invalid workflow transition: {current} -> {next_status}")


def assert_run_transition(current: WorkflowRunStatus, next_status: WorkflowRunStatus) -> None:
    if current == next_status:
        return
    if next_status not in ALLOWED_RUN_TRANSITIONS[current]:
        raise ValueError(f"invalid workflow run transition: {current} -> {next_status}")


@dataclass(frozen=True)
class RequestIntent:
    intent_type: IntentType
    confidence: float
    reason: str
    requires_clarification: bool = False
    clarification_question: str | None = None
    extracted: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.intent_type, str):
            object.__setattr__(self, "intent_type", IntentType(self.intent_type))
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    def to_record(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "requires_clarification": self.requires_clarification,
            "clarification_question": self.clarification_question,
            "extracted": self.extracted,
        }


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    step_type: StepType
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id must not be empty")
        if not self.name:
            raise ValueError("step name must not be empty")
        if isinstance(self.step_type, str):
            object.__setattr__(self, "step_type", StepType(self.step_type))

    def to_record(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "name": self.name,
            "config": self.config,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "WorkflowStep":
        return cls(
            step_id=str(record["step_id"]),
            step_type=StepType(record["step_type"]),
            name=str(record["name"]),
            config=dict(record.get("config") or {}),
            depends_on=list(record.get("depends_on") or []),
        )


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    goal: str
    steps: list[WorkflowStep]
    workflow_id: str = field(default_factory=workflow_id)
    version: int = 1
    description: str = ""
    success_criteria: list[str] = field(default_factory=list)
    owner_channel: str = "web"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    intent_type: IntentType = IntentType.WORKFLOW_DESIGN
    triggers: list[dict[str, Any]] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    evals: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    approved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.workflow_id:
            raise ValueError("workflow_id must not be empty")
        if not self.name:
            raise ValueError("workflow name must not be empty")
        if not self.goal:
            raise ValueError("workflow goal must not be empty")
        if not self.steps:
            raise ValueError("workflow requires at least one step")
        if isinstance(self.status, str):
            object.__setattr__(self, "status", WorkflowStatus(self.status))
        if isinstance(self.intent_type, str):
            object.__setattr__(self, "intent_type", IntentType(self.intent_type))

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "success_criteria": self.success_criteria,
            "owner_channel": self.owner_channel,
            "status": self.status.value,
            "intent_type": self.intent_type.value,
            "triggers": self.triggers,
            "inputs": self.inputs,
            "sources": self.sources,
            "steps": [step.to_record() for step in self.steps],
            "capabilities": self.capabilities,
            "policy": self.policy,
            "outputs": self.outputs,
            "evals": self.evals,
            "assumptions": self.assumptions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "WorkflowSpec":
        return cls(
            workflow_id=str(record["workflow_id"]),
            version=int(record.get("version", 1)),
            name=str(record["name"]),
            description=str(record.get("description") or ""),
            goal=str(record["goal"]),
            success_criteria=list(record.get("success_criteria") or []),
            owner_channel=str(record.get("owner_channel") or "web"),
            status=WorkflowStatus(record.get("status", WorkflowStatus.DRAFT.value)),
            intent_type=IntentType(record.get("intent_type", IntentType.WORKFLOW_DESIGN.value)),
            triggers=list(record.get("triggers") or []),
            inputs=dict(record.get("inputs") or {}),
            sources=list(record.get("sources") or []),
            steps=[WorkflowStep.from_record(item) for item in record.get("steps", [])],
            capabilities=list(record.get("capabilities") or []),
            policy=dict(record.get("policy") or {}),
            outputs=list(record.get("outputs") or []),
            evals=list(record.get("evals") or []),
            assumptions=list(record.get("assumptions") or []),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
            approved_at=record.get("approved_at"),
        )


@dataclass(frozen=True)
class WorkflowRun:
    workflow_id: str
    workflow_version: int
    run_id: str = field(default_factory=workflow_run_id)
    status: WorkflowRunStatus = WorkflowRunStatus.QUEUED
    trigger: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None

    def __post_init__(self) -> None:
        if not self.workflow_id:
            raise ValueError("workflow_id must not be empty")
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if isinstance(self.status, str):
            object.__setattr__(self, "status", WorkflowRunStatus(self.status))

    def to_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status.value,
            "trigger": self.trigger,
            "context": self.context,
            "step_results": self.step_results,
            "artifacts": self.artifacts,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "WorkflowRun":
        return cls(
            run_id=str(record["run_id"]),
            workflow_id=str(record["workflow_id"]),
            workflow_version=int(record["workflow_version"]),
            status=WorkflowRunStatus(record["status"]),
            trigger=dict(record.get("trigger") or {}),
            context=dict(record.get("context") or {}),
            step_results=dict(record.get("step_results") or {}),
            artifacts=list(record.get("artifacts") or []),
            result=record.get("result"),
            error=record.get("error"),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
            started_at=record.get("started_at"),
            completed_at=record.get("completed_at"),
        )


@dataclass(frozen=True)
class WorkflowDesignSession:
    user_request: str
    intent: RequestIntent
    session_id: str = field(default_factory=design_session_id)
    status: str = "designing"
    extracted_slots: dict[str, Any] = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)
    question: str | None = None
    assumptions: list[str] = field(default_factory=list)
    proposed_workflow_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_record(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "user_request": self.user_request,
            "intent": self.intent.to_record(),
            "extracted_slots": self.extracted_slots,
            "missing_slots": self.missing_slots,
            "question": self.question,
            "assumptions": self.assumptions,
            "proposed_workflow_id": self.proposed_workflow_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
