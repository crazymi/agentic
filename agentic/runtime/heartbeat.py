from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


def update_heartbeat(store: TaskStore, task_id: str):
    return store.heartbeat(task_id)


class Watchdog:
    def __init__(
        self,
        store: TaskStore,
        *,
        stale_after_s: float = 300,
        trace: TraceLogger | None = None,
    ):
        self.store = store
        self.stale_after_s = stale_after_s
        self.trace = trace

    def mark_stale_tasks_unhealthy(self) -> list[str]:
        now = datetime.now(timezone.utc)
        marked: list[str] = []
        candidates = self.store.list_tasks(status=DurableTaskStatus.RUNNING) + self.store.list_tasks(
            status=DurableTaskStatus.CANCEL_REQUESTED
        )
        for task in candidates:
            heartbeat = task.last_heartbeat_at or task.started_at or task.updated_at
            heartbeat_at = datetime.fromisoformat(heartbeat)
            if now - heartbeat_at <= timedelta(seconds=self.stale_after_s):
                continue
            self.store.transition(
                task.task_id,
                DurableTaskStatus.UNHEALTHY,
                error={"type": "stale_heartbeat", "message": "task heartbeat is stale"},
                event_type="task_unhealthy",
            )
            marked.append(task.task_id)
            if self.trace is not None:
                self.trace.record("task_unhealthy", {"task_id": task.task_id})
        return marked
