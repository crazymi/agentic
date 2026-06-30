from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from agentic.runtime.durable_channel_loop import DurableChannelLoop
from agentic.runtime.events import InboundMessage
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


class FakeExecutor:
    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        return {"final_answer": f"echo: {task.input['message']}", "ok": True}


class Milestone3DurableChannelLoopTests(unittest.TestCase):
    def test_inbound_message_returns_task_id_immediately_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            pool = TaskPool(store=store, executor=FakeExecutor(), max_workers=1)
            try:
                loop = DurableChannelLoop(store=store, pool=pool, trace=trace)
                response = loop.handle_message(InboundMessage(text="hello"))
                _wait_for_status(store, response.task_id, DurableTaskStatus.COMPLETED)
                completed = store.get_task(response.task_id)
                event_types = [event.event_type for event in trace.read_events()]
            finally:
                pool.shutdown()

        self.assertTrue(response.ok)
        self.assertEqual(completed.result["final_answer"], "echo: hello")
        self.assertIn("channel_message_received", event_types)
        self.assertIn("task_enqueued", event_types)


def _wait_for_status(store: TaskStore, task_id: str, status: DurableTaskStatus) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if store.get_task(task_id).status == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not reach {status}")


if __name__ == "__main__":
    unittest.main()
