from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.runtime.daemon import recover_interrupted_tasks
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore


class Milestone3RecoveryTests(unittest.TestCase):
    def test_recovery_marks_running_and_cancel_requested_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            running = store.create_task(kind="fake", input={})
            cancelling = store.create_task(kind="fake", input={})
            completed = store.create_task(kind="fake", input={})
            store.transition(running.task_id, DurableTaskStatus.RUNNING)
            store.transition(cancelling.task_id, DurableTaskStatus.RUNNING)
            store.transition(cancelling.task_id, DurableTaskStatus.CANCEL_REQUESTED)
            store.transition(completed.task_id, DurableTaskStatus.RUNNING)
            store.transition(completed.task_id, DurableTaskStatus.COMPLETED)

            recovered = recover_interrupted_tasks(store)
            running_status = store.get_task(running.task_id).status
            cancelling_status = store.get_task(cancelling.task_id).status
            completed_status = store.get_task(completed.task_id).status

        self.assertEqual(set(recovered), {running.task_id, cancelling.task_id})
        self.assertEqual(running_status, DurableTaskStatus.UNHEALTHY)
        self.assertEqual(cancelling_status, DurableTaskStatus.UNHEALTHY)
        self.assertEqual(completed_status, DurableTaskStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
