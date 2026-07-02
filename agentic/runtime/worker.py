from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from time import sleep
from typing import Protocol

from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore


class TaskExecutor(Protocol):
    def execute(self, task: TaskRecord, context: "TaskExecutionContext") -> dict:
        ...


@dataclass(frozen=True)
class TaskExecutionContext:
    store: TaskStore

    def heartbeat(self, task_id: str) -> None:
        self.store.heartbeat(task_id)

    def cancellation_requested(self, task_id: str) -> bool:
        return self.store.get_task(task_id).status == DurableTaskStatus.CANCEL_REQUESTED

    def raise_if_cancelled(self, task_id: str) -> None:
        if self.cancellation_requested(task_id):
            raise TaskCancelled(f"task cancellation requested: {task_id}")


class TaskCancelled(Exception):
    pass


class TaskWorker:
    def __init__(
        self,
        store: TaskStore,
        executor: TaskExecutor,
        *,
        heartbeat_interval_s: float = 15.0,
    ):
        self.store = store
        self.executor = executor
        self.heartbeat_interval_s = heartbeat_interval_s

    def run_claimed_task(self, task: TaskRecord) -> TaskRecord:
        context = TaskExecutionContext(self.store)
        stop_heartbeat = Event()
        heartbeat_thread = self._start_heartbeat_loop(task.task_id, stop_heartbeat)
        try:
            context.raise_if_cancelled(task.task_id)
            result = self.executor.execute(task, context)
            latest = self.store.get_task(task.task_id)
            if latest.status == DurableTaskStatus.CANCEL_REQUESTED:
                return self.store.transition(
                    task.task_id,
                    DurableTaskStatus.CANCELLED,
                    event_type="task_cancelled",
                )
            return self.store.transition(
                task.task_id,
                DurableTaskStatus.COMPLETED,
                result=result,
                event_type="task_completed",
            )
        except TaskCancelled as exc:
            return self.store.transition(
                task.task_id,
                DurableTaskStatus.CANCELLED,
                error={"type": type(exc).__name__, "message": str(exc)},
                event_type="task_cancelled",
            )
        except Exception as exc:
            return self.store.transition(
                task.task_id,
                DurableTaskStatus.FAILED,
                error={"type": type(exc).__name__, "message": str(exc)},
                event_type="task_failed",
            )
        finally:
            stop_heartbeat.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=1.0)

    def _start_heartbeat_loop(self, task_id: str, stop: Event) -> Thread | None:
        if self.heartbeat_interval_s <= 0:
            return None

        def _beat() -> None:
            while not stop.wait(self.heartbeat_interval_s):
                try:
                    self.store.heartbeat(task_id)
                except ValueError:
                    return

        thread = Thread(target=_beat, name=f"task-heartbeat-{task_id}", daemon=True)
        thread.start()
        return thread
