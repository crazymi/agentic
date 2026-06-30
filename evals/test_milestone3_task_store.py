from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore


class Milestone3TaskStoreTests(unittest.TestCase):
    def test_create_and_reload_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.sqlite3"
            store = TaskStore(path)
            task = store.create_task(kind="chat_turn", input={"message": "hi"})
            reloaded = TaskStore(path).get_task(task.task_id)

        self.assertEqual(reloaded.kind, "chat_turn")
        self.assertEqual(reloaded.input["message"], "hi")
        self.assertEqual(reloaded.status, DurableTaskStatus.QUEUED)

    def test_valid_transition_and_result_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            store.transition(task.task_id, DurableTaskStatus.RUNNING)
            completed = store.transition(
                task.task_id,
                DurableTaskStatus.COMPLETED,
                result={"answer": "ok"},
            )
            reloaded = TaskStore(Path(tmpdir) / "state.sqlite3").get_task(task.task_id)

        self.assertEqual(completed.result, {"answer": "ok"})
        self.assertEqual(reloaded.result, {"answer": "ok"})

    def test_invalid_transition_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})

            with self.assertRaises(ValueError):
                store.transition(task.task_id, DurableTaskStatus.COMPLETED)

    def test_events_are_ordered_and_durable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.sqlite3"
            store = TaskStore(path)
            task = store.create_task(kind="fake", input={})
            store.append_event(task.task_id, "one", {"n": 1})
            store.append_event(task.task_id, "two", {"n": 2})
            events = TaskStore(path).list_events(task.task_id)

        self.assertEqual([event["event_type"] for event in events], ["task_created", "one", "two"])


if __name__ == "__main__":
    unittest.main()
