from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from agentic.runtime.events import ensure_json_payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approval_id() -> str:
    return f"appr_{uuid4().hex}"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


TERMINAL_STATUSES = {
    ApprovalStatus.APPROVED,
    ApprovalStatus.DENIED,
    ApprovalStatus.EXPIRED,
}


@dataclass(frozen=True)
class ApprovalRequest:
    capability: str
    reason: str
    payload: dict[str, Any]
    approval_id: str = field(default_factory=_approval_id)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.approval_id:
            raise ValueError("approval_id must not be empty")
        if not self.capability:
            raise ValueError("capability must not be empty")
        object.__setattr__(self, "payload", ensure_json_payload(self.payload))
        if isinstance(self.status, str):
            object.__setattr__(self, "status", ApprovalStatus(self.status))

    def transition(self, status: ApprovalStatus) -> "ApprovalRequest":
        if self.status in TERMINAL_STATUSES:
            raise ValueError(
                f"approval {self.approval_id} is already {self.status.value}"
            )
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"cannot transition from {self.status.value}")
        return replace(self, status=status, updated_at=_now())

    def to_record(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "capability": self.capability,
            "reason": self.reason,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ApprovalRequest":
        return cls(
            approval_id=str(record["approval_id"]),
            capability=str(record["capability"]),
            reason=str(record["reason"]),
            payload=dict(record.get("payload", {})),
            status=ApprovalStatus(str(record["status"])),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )
