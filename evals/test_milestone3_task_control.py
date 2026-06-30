from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from agentic.runtime.task_control import TaskControl
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutionContext, TaskCancelled
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore


class CancellableExecutor:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        self.started.set()
        self.release.wait(timeout=5)
        context.raise_if_cancelled(task.task_id)
        return {"ok": True}


class Milestone3TaskControlTests(unittest.TestCase):
    def test_queued_task_can_be_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})

            cancelled = TaskControl(store).request_cancel(task.task_id)

        self.assertEqual(cancelled.status, DurableTaskStatus.CANCELLED)

    def test_pause_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            control = TaskControl(store)

            paused = control.pause(task.task_id)
            resumed = control.resume(task.task_id)

        self.assertEqual(paused.status, DurableTaskStatus.PAUSED)
        self.assertEqual(resumed.status, DurableTaskStatus.QUEUED)

    def test_running_task_observes_cancel_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            executor = CancellableExecutor()
            pool = TaskPool(store=store, executor=executor, max_workers=1)
            try:
                pool.kick()
                self.assertTrue(executor.started.wait(timeout=2))
                requested = TaskControl(store).request_cancel(task.task_id)
                executor.release.set()
                _wait_for_status(store, task.task_id, DurableTaskStatus.CANCELLED)
                latest = store.get_task(task.task_id)
            finally:
                pool.shutdown()

        self.assertEqual(requested.status, DurableTaskStatus.CANCEL_REQUESTED)
        self.assertEqual(latest.status, DurableTaskStatus.CANCELLED)


def _wait_for_status(store: TaskStore, task_id: str, status: DurableTaskStatus) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if store.get_task(task_id).status == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not reach {status}")


if __name__ == "__main__":
    unittest.main()
