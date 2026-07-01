from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from agentic.workflow_kernel.models import utc_now


def tooling_request_id() -> str:
    return f"tooling_{uuid4().hex}"


class ToolingKind(StrEnum):
    CONNECTOR = "connector"
    TOOL = "tool"
    RUNTIME = "runtime"
    POLICY = "policy"
    ARTIFACT_REVIEW = "artifact_review"
    SKILL = "skill"


class ToolingStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ToolingRequest:
    capability: str
    kind: ToolingKind
    reason: str
    action: str = ""
    resource: str = ""
    suggested_module: str = ""
    priority: int = 2
    status: ToolingStatus = ToolingStatus.PROPOSED
    payload: dict[str, Any] = field(default_factory=dict)
    tooling_id: str = field(default_factory=tooling_request_id)
    workflow_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.capability:
            raise ValueError("capability must not be empty")
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", ToolingKind(self.kind))
        if isinstance(self.status, str):
            object.__setattr__(self, "status", ToolingStatus(self.status))
        if not 0 <= self.priority <= 3:
            raise ValueError("priority must be between 0 and 3")

    def to_record(self) -> dict[str, Any]:
        return {
            "tooling_id": self.tooling_id,
            "workflow_id": self.workflow_id,
            "capability": self.capability,
            "kind": self.kind.value,
            "action": self.action,
            "resource": self.resource,
            "reason": self.reason,
            "suggested_module": self.suggested_module,
            "priority": self.priority,
            "status": self.status.value,
            "payload": self.payload,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ToolingRequest":
        return cls(
            tooling_id=str(record["tooling_id"]),
            workflow_id=record.get("workflow_id"),
            capability=str(record["capability"]),
            kind=ToolingKind(record["kind"]),
            action=str(record.get("action") or ""),
            resource=str(record.get("resource") or ""),
            reason=str(record.get("reason") or ""),
            suggested_module=str(record.get("suggested_module") or ""),
            priority=int(record.get("priority", 2)),
            status=ToolingStatus(record.get("status", ToolingStatus.PROPOSED.value)),
            payload=dict(record.get("payload") or {}),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )


@dataclass(frozen=True)
class ToolingPlan:
    workflow_id: str
    requests: list[ToolingRequest]

    @property
    def has_blocking_work(self) -> bool:
        return bool(self.requests)

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "has_blocking_work": self.has_blocking_work,
            "requests": [request.to_record() for request in self.requests],
        }

