from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agentic.runtime.heartbeat import Watchdog, update_heartbeat
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore


class Milestone3HeartbeatTests(unittest.TestCase):
    def test_running_task_heartbeat_updates_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            running = store.transition(task.task_id, DurableTaskStatus.RUNNING)
            updated = update_heartbeat(store, running.task_id)

        self.assertIsNotNone(updated.last_heartbeat_at)

    def test_watchdog_marks_stale_task_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.sqlite3"
            store = TaskStore(path)
            task = store.create_task(kind="fake", input={})
            store.transition(task.task_id, DurableTaskStatus.RUNNING)
            old = (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat()
            with sqlite3.connect(path) as conn:
                conn.execute(
                    "update tasks set last_heartbeat_at = ? where task_id = ?",
                    (old, task.task_id),
                )
            marked = Watchdog(store, stale_after_s=1).mark_stale_tasks_unhealthy()
            latest = store.get_task(task.task_id)

        self.assertEqual(marked, [task.task_id])
        self.assertEqual(latest.status, DurableTaskStatus.UNHEALTHY)

    def test_watchdog_ignores_terminal_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            store.transition(task.task_id, DurableTaskStatus.RUNNING)
            store.transition(task.task_id, DurableTaskStatus.COMPLETED)
            marked = Watchdog(store, stale_after_s=0).mark_stale_tasks_unhealthy()

        self.assertEqual(marked, [])


if __name__ == "__main__":
    unittest.main()
