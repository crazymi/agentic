from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from agentic.runtime.subagent_loop import SubagentLoop
from agentic.runtime.tool_bridge import ToolBridge, ToolExecutionResult
from agentic.tasks.subagent_task import SubAgentTask, TaskState
from agentic.traces.logger import TraceLogger


@dataclass
class FakeResponse:
    text: str


class FakeSubagent:
    def __init__(self, text: str):
        self.text = text
        self.tasks: list[SubAgentTask] = []

    def generate_for_task(self, task: SubAgentTask) -> FakeResponse:
        self.tasks.append(task)
        return FakeResponse(self.text)


class FakeToolBridge:
    def __init__(self, result: ToolExecutionResult):
        self.result = result
        self.calls: list[str] = []

    def execute_tool_call_text(self, text: str) -> ToolExecutionResult:
        self.calls.append(text)
        return self.result


class Phase1SubagentLoopTests(unittest.TestCase):
    def test_subagent_loop_executes_tool_call(self) -> None:
        agent = FakeSubagent('{"tool":"add","arguments":{"a":1,"b":1}}')
        bridge = FakeToolBridge(ToolExecutionResult(tool="add", ok=True, result=2))
        task = SubAgentTask("Compute 1+1.")
        loop = SubagentLoop(agent=agent, tool_bridge=bridge)

        result = loop.run_once(task)

        self.assertTrue(result.ok)
        self.assertEqual(bridge.calls, ['{"tool":"add","arguments":{"a":1,"b":1}}'])
        self.assertEqual(agent.tasks, [task])

    def test_subagent_loop_marks_task_completed(self) -> None:
        task = SubAgentTask("Compute 1+1.")
        loop = SubagentLoop(
            agent=FakeSubagent('{"tool":"add","arguments":{"a":1,"b":1}}'),
            tool_bridge=ToolBridge(),
        )

        result = loop.run_once(task)

        self.assertTrue(result.ok)
        self.assertEqual(task.state, TaskState.COMPLETED)
        self.assertEqual(task.result, "2")
        self.assertEqual(result.report, "2")

    def test_subagent_loop_records_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            task = SubAgentTask("Compute 1+1.")
            loop = SubagentLoop(
                agent=FakeSubagent('{"tool":"add","arguments":{"a":1,"b":1}}'),
                tool_bridge=ToolBridge(trace=trace),
                trace=trace,
            )

            result = loop.run_once(task)
            event_types = [event.event_type for event in trace.read_events()]

        self.assertTrue(result.ok)
        self.assertIn("subagent_model_called", event_types)
        self.assertIn("tool_called:add", event_types)
        self.assertIn("tool_result:add", event_types)
        self.assertIn("subagent_reported", event_types)

    def test_subagent_loop_marks_failed_on_bad_tool_call(self) -> None:
        task = SubAgentTask("Compute 1+1.")
        loop = SubagentLoop(agent=FakeSubagent("{not json"), tool_bridge=ToolBridge())

        result = loop.run_once(task)

        self.assertFalse(result.ok)
        self.assertEqual(task.state, TaskState.FAILED)
        self.assertIsNone(task.result)
        self.assertEqual(result.error_type, "malformed_tool_call")


if __name__ == "__main__":
    unittest.main()
