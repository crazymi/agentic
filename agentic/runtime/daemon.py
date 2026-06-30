from __future__ import annotations

from pathlib import Path

from agentic.config.settings import AppConfig
from agentic.runtime.heartbeat import Watchdog
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutor
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


def default_state_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "agentic.sqlite3"


def recover_interrupted_tasks(store: TaskStore, trace: TraceLogger | None = None) -> list[str]:
    recovered: list[str] = []
    for status in (DurableTaskStatus.RUNNING, DurableTaskStatus.CANCEL_REQUESTED):
        for task in store.list_tasks(status=status):
            store.transition(
                task.task_id,
                DurableTaskStatus.UNHEALTHY,
                error={"type": "runtime_restart", "message": "task interrupted by restart"},
                event_type="task_recovered_unhealthy",
            )
            recovered.append(task.task_id)
            if trace is not None:
                trace.record("task_recovered_unhealthy", {"task_id": task.task_id})
    return recovered


class DurableRuntime:
    def __init__(
        self,
        *,
        store: TaskStore,
        pool: TaskPool,
        watchdog: Watchdog,
    ):
        self.store = store
        self.pool = pool
        self.watchdog = watchdog

    @classmethod
    def from_config(
        cls,
        config: AppConfig,
        *,
        executor: TaskExecutor,
        trace: TraceLogger,
        max_workers: int = 1,
    ) -> "DurableRuntime":
        store = TaskStore(default_state_db(config))
        recover_interrupted_tasks(store, trace=trace)
        pool = TaskPool(store=store, executor=executor, max_workers=max_workers)
        watchdog = Watchdog(store, trace=trace)
        return cls(store=store, pool=pool, watchdog=watchdog)

    def start(self) -> None:
        self.watchdog.mark_stale_tasks_unhealthy()
        self.pool.kick()

    def shutdown(self) -> None:
        self.pool.shutdown(wait=False)
