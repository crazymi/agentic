from __future__ import annotations

from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore


class TaskControl:
    def __init__(self, store: TaskStore):
        self.store = store

    def request_cancel(self, task_id: str):
        task = self.store.get_task(task_id)
        if task.status in {DurableTaskStatus.QUEUED, DurableTaskStatus.PAUSED}:
            return self.store.transition(
                task_id,
                DurableTaskStatus.CANCELLED,
                event_type="task_cancelled",
            )
        if task.status == DurableTaskStatus.RUNNING:
            return self.store.transition(
                task_id,
                DurableTaskStatus.CANCEL_REQUESTED,
                event_type="task_cancel_requested",
            )
        return task

    def pause(self, task_id: str):
        return self.store.transition(
            task_id,
            DurableTaskStatus.PAUSED,
            event_type="task_paused",
        )

    def resume(self, task_id: str):
        return self.store.transition(
            task_id,
            DurableTaskStatus.QUEUED,
            event_type="task_resumed",
        )
