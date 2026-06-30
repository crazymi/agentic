from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.traces.logger import TraceLogger
from agentic.traces.replay import TraceReplay


class Phase1TraceReplayTests(unittest.TestCase):
    def test_replay_loads_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.jsonl"
            logger = TraceLogger(trace_path)
            logger.record("user_message_received", {"message": "1+1은 뭐지?"})
            logger.record("master_model_called", {"role": "master"})

            replay = TraceReplay.from_path(trace_path)

        self.assertEqual(len(replay.events), 2)
        self.assertEqual(
            replay.event_types(),
            ["user_message_received", "master_model_called"],
        )

    def test_replay_filters_by_type(self) -> None:
        replay = _replay_with_events(
            [
                "master_model_called",
                "tool_called:add",
                "tool_result:add",
                "tool_called:add",
            ]
        )

        events = replay.filter_by_type("tool_called:add")

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].payload["index"], 1)
        self.assertEqual(events[1].payload["index"], 3)

    def test_replay_asserts_ordered_events(self) -> None:
        replay = _replay_with_events(
            [
                "user_message_received",
                "master_model_called",
                "master_delegation_decision",
                "subagent_task_created",
                "tool_called:add",
                "tool_result:add",
            ]
        )

        replay.assert_ordered_events(
            [
                "master_model_called",
                "subagent_task_created",
                "tool_result:add",
            ]
        )

    def test_replay_reports_missing_event(self) -> None:
        replay = _replay_with_events(
            [
                "master_model_called",
                "tool_result:add",
                "tool_called:add",
            ]
        )

        with self.assertRaisesRegex(
            AssertionError,
            "missing expected event 'tool_result:add' at or after index 3",
        ):
            replay.assert_ordered_events(["tool_called:add", "tool_result:add"])

    def test_replay_finds_last_event(self) -> None:
        replay = _replay_with_events(
            ["tool_result:add", "master_final_answer", "tool_result:add"]
        )

        self.assertEqual(replay.last_event().event_type, "tool_result:add")
        self.assertEqual(replay.last_event("master_final_answer").payload["index"], 1)
        self.assertIsNone(replay.last_event("missing"))


def _replay_with_events(event_types: list[str]) -> TraceReplay:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        logger = TraceLogger(trace_path)
        for index, event_type in enumerate(event_types):
            logger.record(event_type, {"index": index})
        return TraceReplay.from_path(trace_path)


if __name__ == "__main__":
    unittest.main()
