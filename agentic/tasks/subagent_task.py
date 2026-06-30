from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class TaskState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    TOOL_REQUESTED = "tool_requested"
    TOOL_COMPLETED = "tool_completed"
    REPORTED = "reported"
    COMPLETED = "completed"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.CREATED: {TaskState.RUNNING, TaskState.FAILED},
    TaskState.RUNNING: {TaskState.TOOL_REQUESTED, TaskState.REPORTED, TaskState.FAILED},
    TaskState.TOOL_REQUESTED: {TaskState.TOOL_COMPLETED, TaskState.FAILED},
    TaskState.TOOL_COMPLETED: {TaskState.REPORTED, TaskState.FAILED},
    TaskState.REPORTED: {TaskState.COMPLETED, TaskState.FAILED},
    TaskState.COMPLETED: set(),
    TaskState.FAILED: set(),
}


@dataclass
class SubAgentTask:
    instruction: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.CREATED
    result: str | None = None

    def transition(self, next_state: TaskState) -> None:
        if next_state not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid task transition: {self.state} -> {next_state}")
        self.state = next_state

    def mark_result(self, result: str) -> None:
        self.result = result
        self.transition(TaskState.REPORTED)
