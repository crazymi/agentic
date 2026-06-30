from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agentic.tasks.subagent_task import SubAgentTask, TaskState


class TaskTraceRecorder(Protocol):
    def record(self, event_type: str, payload: dict) -> object:
        ...


class UnknownTaskError(KeyError):
    def __init__(self, task_id: str):
        super().__init__(f"unknown task id: {task_id}")
        self.task_id = task_id


@dataclass
class TaskLedger:
    trace: TaskTraceRecorder | None = None
    _tasks: dict[str, SubAgentTask] = field(default_factory=dict)

    def create_task(self, instruction: str) -> SubAgentTask:
        task = SubAgentTask(instruction=instruction)
        self._tasks[task.task_id] = task
        self._record(
            "subagent_task_created",
            {
                "task_id": task.task_id,
                "instruction": task.instruction,
                "state": task.state.value,
            },
        )
        return task

    def get_task(self, task_id: str) -> SubAgentTask:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise UnknownTaskError(task_id) from exc

    def list_tasks(self) -> list[SubAgentTask]:
        return list(self._tasks.values())

    def transition_task(
        self,
        task_id: str,
        next_state: TaskState | str,
    ) -> SubAgentTask:
        task = self.get_task(task_id)
        state = TaskState(next_state)
        previous_state = task.state

        task.transition(state)
        self._record_transition(task, previous_state, state)
        return task

    def report_task(self, task_id: str, result: str) -> SubAgentTask:
        task = self.get_task(task_id)
        previous_state = task.state

        task.mark_result(result)
        self._record_transition(task, previous_state, task.state)
        return task

    def _record_transition(
        self,
        task: SubAgentTask,
        previous_state: TaskState,
        next_state: TaskState,
    ) -> None:
        self._record(
            "subagent_task_state_changed",
            {
                "task_id": task.task_id,
                "from": previous_state.value,
                "to": next_state.value,
            },
        )

    def _record(self, event_type: str, payload: dict) -> None:
        if self.trace is not None:
            self.trace.record(event_type, payload)
