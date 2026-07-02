from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore


class EchoExecutor:
    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        return {"echo": task.input.get("value")}


class FailingExecutor:
    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        raise RuntimeError("boom")


class BlockingExecutor:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        self.started.set()
        self.release.wait(timeout=5)
        return {"done": task.task_id}


class Milestone3TaskPoolTests(unittest.TestCase):
    def test_queued_task_runs_to_completion(self) -> None:
        with _store() as store:
            task = store.create_task(kind="echo", input={"value": "hi"})
            pool = TaskPool(store=store, executor=EchoExecutor(), max_workers=1)
            try:
                pool.kick()
                _wait_for_status(store, task.task_id, DurableTaskStatus.COMPLETED)
                completed = store.get_task(task.task_id)
            finally:
                pool.shutdown()

        self.assertEqual(completed.result, {"echo": "hi"})

    def test_failed_task_stores_error(self) -> None:
        with _store() as store:
            task = store.create_task(kind="fail", input={})
            pool = TaskPool(store=store, executor=FailingExecutor(), max_workers=1)
            try:
                pool.kick()
                _wait_for_status(store, task.task_id, DurableTaskStatus.FAILED)
                failed = store.get_task(task.task_id)
            finally:
                pool.shutdown()

        self.assertEqual(failed.error["type"], "RuntimeError")

    def test_max_concurrency_is_respected(self) -> None:
        with _store() as store:
            first = store.create_task(kind="block", input={})
            second = store.create_task(kind="block", input={})
            executor = BlockingExecutor()
            pool = TaskPool(store=store, executor=executor, max_workers=1)
            try:
                pool.kick()
                self.assertTrue(executor.started.wait(timeout=2))
                self.assertEqual(store.get_task(first.task_id).status, DurableTaskStatus.RUNNING)
                self.assertEqual(store.get_task(second.task_id).status, DurableTaskStatus.QUEUED)
                executor.release.set()
                _wait_for_status(store, first.task_id, DurableTaskStatus.COMPLETED)
            finally:
                pool.shutdown()

    def test_claim_next_claims_once(self) -> None:
        with _store() as store:
            task = store.create_task(kind="fake", input={})
            first = store.claim_next()
            second = store.claim_next()

        self.assertEqual(first.task_id, task.task_id)
        self.assertIsNone(second)

    def test_worker_refreshes_heartbeat_during_long_executor(self) -> None:
        with _store() as store:
            task = store.create_task(kind="block", input={})
            executor = BlockingExecutor()
            pool = TaskPool(
                store=store,
                executor=executor,
                max_workers=1,
                heartbeat_interval_s=0.05,
            )
            try:
                pool.kick()
                self.assertTrue(executor.started.wait(timeout=2))
                _wait_for_event_count(store, task.task_id, "task_heartbeat", count=2)
                running = store.get_task(task.task_id)
                executor.release.set()
                _wait_for_status(store, task.task_id, DurableTaskStatus.COMPLETED)
            finally:
                pool.shutdown()

        self.assertEqual(running.status, DurableTaskStatus.RUNNING)
        self.assertIsNotNone(running.last_heartbeat_at)


class _store:
    def __enter__(self) -> TaskStore:
        self.tmpdir = tempfile.TemporaryDirectory()
        return TaskStore(Path(self.tmpdir.name) / "state.sqlite3")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmpdir.cleanup()


def _wait_for_status(store: TaskStore, task_id: str, status: DurableTaskStatus) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if store.get_task(task_id).status == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not reach {status}")


def _wait_for_event_count(
    store: TaskStore,
    task_id: str,
    event_type: str,
    *,
    count: int,
) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        events = [
            event
            for event in store.list_events(task_id)
            if event["event_type"] == event_type
        ]
        if len(events) >= count:
            return
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not record {count} {event_type} events")


if __name__ == "__main__":
    unittest.main()
