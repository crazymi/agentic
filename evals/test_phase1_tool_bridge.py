from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.runtime.tool_bridge import ToolBridge
from agentic.traces.logger import TraceLogger


class Phase1ToolBridgeTests(unittest.TestCase):
    def test_bridge_executes_add_tool(self) -> None:
        bridge = ToolBridge()

        result = bridge.execute_tool_call_text(
            '{"tool":"add","arguments":{"a":1,"b":1}}'
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.tool, "add")
        self.assertEqual(result.result, 2)

    def test_bridge_records_tool_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            bridge = ToolBridge(trace=trace)

            result = bridge.execute_tool_call_text(
                '{"tool":"add","arguments":{"a":1,"b":1}}'
            )
            events = trace.read_events()

        self.assertTrue(result.ok)
        self.assertEqual(
            [event.event_type for event in events],
            ["tool_called:add", "tool_result:add"],
        )
        self.assertEqual(events[0].payload["arguments"], {"a": 1, "b": 1})
        self.assertEqual(events[1].payload["result"], 2)

    def test_bridge_handles_malformed_json(self) -> None:
        bridge = ToolBridge()

        result = bridge.execute_tool_call_text("{not json")

        self.assertFalse(result.ok)
        self.assertIsNone(result.tool)
        self.assertEqual(result.error_type, "malformed_tool_call")
        self.assertIn("invalid tool call JSON", result.error_message or "")

    def test_bridge_handles_unknown_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            bridge = ToolBridge(trace=trace)

            result = bridge.execute_tool_call_text(
                '{"tool":"multiply","arguments":{"a":2,"b":3}}'
            )
            events = trace.read_events()

        self.assertFalse(result.ok)
        self.assertEqual(result.tool, "multiply")
        self.assertEqual(result.error_type, "unknown_tool")
        self.assertIn("unknown tool", result.error_message or "")
        self.assertEqual(
            [event.event_type for event in events],
            ["tool_called:multiply", "tool_result:multiply"],
        )
        self.assertFalse(events[1].payload["ok"])


if __name__ == "__main__":
    unittest.main()
