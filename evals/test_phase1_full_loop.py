from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.models.local_gguf import ModelResponse
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.runtime.subagent_loop import SubagentLoop
from agentic.runtime.tool_bridge import ToolBridge
from agentic.runtime.turn import MasterTurn
from agentic.tasks.ledger import TaskLedger
from agentic.tasks.subagent_task import TaskState
from agentic.traces.logger import TraceLogger
from agentic.traces.replay import TraceReplay


class FakeMasterAgent:
    def __init__(self, text: str):
        self.text = text
        self.messages: list[str] = []

    def generate(self, user_message: str) -> ModelResponse:
        self.messages.append(user_message)
        return ModelResponse(
            text=self.text,
            command=("fake-master",),
            returncode=0,
            raw_text=self.text,
        )


class FakeSubagent:
    def __init__(self, text: str):
        self.text = text

    def generate_for_task(self, task) -> ModelResponse:
        return ModelResponse(
            text=self.text,
            command=("fake-subagent",),
            returncode=0,
            raw_text=self.text,
        )


class Phase1FullLoopTests(unittest.TestCase):
    def test_full_loop_answers_addition_with_fake_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run_user_message("1+1은 뭐지?")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "2")
        self.assertIsNotNone(result.task)
        self.assertEqual(result.task.state, TaskState.COMPLETED)
        self.assertEqual(result.task.result, "2")

    def test_full_loop_trace_contains_expected_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.jsonl"
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("1+1은 뭐지?")
            replay = TraceReplay.from_path(trace_path)

        self.assertTrue(result.ok)
        replay.assert_ordered_events(
            [
                "user_message_received",
                "master_model_called",
                "master_delegation_decision",
                "subagent_task_created",
                "subagent_model_called",
                "tool_called:add",
                "tool_result:add",
                "subagent_reported",
                "master_final_answer",
            ]
        )

    def test_full_loop_returns_direct_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text='{"action":"answer","answer":"hello"}',
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("Say hello.")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "hello")
        self.assertIsNone(result.task)

    def test_full_loop_accepts_phase1_decision_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text='{"decision":"answer","answer":"2"}',
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("Answer directly.")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "2")

    def test_full_loop_returns_failure_result_on_subagent_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text="{not json",
            )

            result = runtime.run("1+1은 뭐지?")

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "malformed_tool_call")
        self.assertIn("Failed:", result.final_answer)
        self.assertIsNotNone(result.task)
        self.assertEqual(result.task.state, TaskState.FAILED)


def _runtime(
    tmpdir: str,
    *,
    master_text: str,
    subagent_text: str,
) -> FullLoopRuntime:
    trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
    return FullLoopRuntime(
        master_turn=MasterTurn(FakeMasterAgent(master_text), trace=trace),  # type: ignore[arg-type]
        subagent_loop=SubagentLoop(
            agent=FakeSubagent(subagent_text),
            tool_bridge=ToolBridge(trace=trace),
            trace=trace,
        ),
        ledger=TaskLedger(trace=trace),
        trace=trace,
    )


if __name__ == "__main__":
    unittest.main()
