from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.tasks.ledger import TaskLedger, UnknownTaskError
from agentic.tasks.subagent_task import TaskState
from agentic.traces.logger import TraceLogger


class Phase1TaskLedgerTests(unittest.TestCase):
    def test_ledger_creates_task(self) -> None:
        ledger = TaskLedger()

        task = ledger.create_task("Compute 1+1.")

        self.assertTrue(task.task_id)
        self.assertEqual(task.instruction, "Compute 1+1.")
        self.assertEqual(task.state, TaskState.CREATED)
        self.assertEqual(ledger.list_tasks(), [task])

    def test_ledger_gets_task_by_id(self) -> None:
        ledger = TaskLedger()
        task = ledger.create_task("Compute 1+1.")

        found = ledger.get_task(task.task_id)

        self.assertIs(found, task)

    def test_ledger_records_state_transition(self) -> None:
        ledger = TaskLedger()
        task = ledger.create_task("Compute 1+1.")

        updated = ledger.transition_task(task.task_id, TaskState.RUNNING)

        self.assertIs(updated, task)
        self.assertEqual(task.state, TaskState.RUNNING)

    def test_ledger_rejects_unknown_task(self) -> None:
        ledger = TaskLedger()

        with self.assertRaisesRegex(UnknownTaskError, "unknown task id: missing"):
            ledger.get_task("missing")

    def test_ledger_uses_existing_invalid_transition_rules(self) -> None:
        ledger = TaskLedger()
        task = ledger.create_task("Compute 1+1.")

        with self.assertRaisesRegex(ValueError, "invalid task transition"):
            ledger.transition_task(task.task_id, TaskState.COMPLETED)

    def test_ledger_transitions_through_phase1_lifecycle(self) -> None:
        ledger = TaskLedger()
        task = ledger.create_task("Compute 1+1.")

        ledger.transition_task(task.task_id, TaskState.RUNNING)
        ledger.transition_task(task.task_id, TaskState.TOOL_REQUESTED)
        ledger.transition_task(task.task_id, TaskState.TOOL_COMPLETED)
        ledger.report_task(task.task_id, "2")
        ledger.transition_task(task.task_id, TaskState.COMPLETED)

        self.assertEqual(task.state, TaskState.COMPLETED)
        self.assertEqual(task.result, "2")

    def test_ledger_optionally_records_trace_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            ledger = TaskLedger(trace=trace)

            task = ledger.create_task("Compute 1+1.")
            ledger.transition_task(task.task_id, TaskState.RUNNING)
            events = trace.read_events()

        self.assertEqual(
            [event.event_type for event in events],
            ["subagent_task_created", "subagent_task_state_changed"],
        )
        self.assertEqual(events[1].payload["from"], "created")
        self.assertEqual(events[1].payload["to"], "running")


if __name__ == "__main__":
    unittest.main()
