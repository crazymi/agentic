from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_id() -> str:
    return f"task_{uuid4().hex}"


class DurableTaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    UNHEALTHY = "unhealthy"


TERMINAL_STATUSES = {
    DurableTaskStatus.CANCELLED,
    DurableTaskStatus.COMPLETED,
    DurableTaskStatus.FAILED,
    DurableTaskStatus.UNHEALTHY,
}


ALLOWED_DURABLE_TRANSITIONS: dict[DurableTaskStatus, set[DurableTaskStatus]] = {
    DurableTaskStatus.QUEUED: {
        DurableTaskStatus.RUNNING,
        DurableTaskStatus.PAUSED,
        DurableTaskStatus.CANCELLED,
        DurableTaskStatus.FAILED,
        DurableTaskStatus.UNHEALTHY,
    },
    DurableTaskStatus.PAUSED: {
        DurableTaskStatus.QUEUED,
        DurableTaskStatus.CANCELLED,
        DurableTaskStatus.UNHEALTHY,
    },
    DurableTaskStatus.RUNNING: {
        DurableTaskStatus.CANCEL_REQUESTED,
        DurableTaskStatus.COMPLETED,
        DurableTaskStatus.FAILED,
        DurableTaskStatus.UNHEALTHY,
    },
    DurableTaskStatus.CANCEL_REQUESTED: {
        DurableTaskStatus.CANCELLED,
        DurableTaskStatus.FAILED,
        DurableTaskStatus.UNHEALTHY,
    },
    DurableTaskStatus.CANCELLED: set(),
    DurableTaskStatus.COMPLETED: set(),
    DurableTaskStatus.FAILED: set(),
    DurableTaskStatus.UNHEALTHY: set(),
}


def assert_transition(
    current: DurableTaskStatus,
    next_status: DurableTaskStatus,
) -> None:
    if next_status == current:
        return
    if next_status not in ALLOWED_DURABLE_TRANSITIONS[current]:
        raise ValueError(f"invalid durable task transition: {current} -> {next_status}")


@dataclass(frozen=True)
class TaskRecord:
    kind: str
    input: dict[str, Any]
    task_id: str = field(default_factory=task_id)
    status: DurableTaskStatus = DurableTaskStatus.QUEUED
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    last_heartbeat_at: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.kind:
            raise ValueError("kind must not be empty")
        if isinstance(self.status, str):
            object.__setattr__(self, "status", DurableTaskStatus(self.status))

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES
