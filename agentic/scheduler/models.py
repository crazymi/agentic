from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from agentic.workflow_kernel.models import utc_now


def schedule_id() -> str:
    return f"sch_{uuid4().hex}"


class ScheduleStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


@dataclass(frozen=True)
class ScheduleRecord:
    workflow_id: str
    trigger: dict[str, Any]
    schedule_id: str = field(default_factory=schedule_id)
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            object.__setattr__(self, "status", ScheduleStatus(self.status))
        if not self.workflow_id:
            raise ValueError("workflow_id must not be empty")
        if not self.trigger:
            raise ValueError("schedule trigger must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "trigger": self.trigger,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ScheduleRecord":
        return cls(
            schedule_id=str(record["schedule_id"]),
            workflow_id=str(record["workflow_id"]),
            status=ScheduleStatus(record["status"]),
            trigger=dict(record.get("trigger") or {}),
            last_run_at=record.get("last_run_at"),
            next_run_at=record.get("next_run_at"),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )
