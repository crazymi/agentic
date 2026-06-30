from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.events import InboundMessage
from agentic.traces.logger import TraceLogger


class FakeFullLoopRuntime:
    def run_user_message(self, message: str):
        class Result:
            ok = True
            final_answer = f"answer: {message}"
            error_type = None
            error_message = None

        return Result()


class FailingFullLoopRuntime:
    def run_user_message(self, message: str):
        raise RuntimeError("boom")


class Milestone2ChannelLoopTests(unittest.TestCase):
    def test_channel_loop_runs_runtime_and_records_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            loop = ChannelLoop(FakeFullLoopRuntime(), trace)  # type: ignore[arg-type]

            response = loop.handle_message(InboundMessage(text="hello"))
            events = [event.event_type for event in trace.read_events()]

        self.assertTrue(response.ok)
        self.assertEqual(response.text, "answer: hello")
        self.assertEqual(events, ["channel_message_received", "channel_response_sent"])

    def test_empty_message_returns_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            loop = ChannelLoop(FakeFullLoopRuntime(), trace)  # type: ignore[arg-type]

            response = loop.handle_message(InboundMessage(text=" "))

        self.assertFalse(response.ok)
        self.assertEqual(response.error_type, "empty_message")

    def test_runtime_failure_returns_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            loop = ChannelLoop(FailingFullLoopRuntime(), trace)  # type: ignore[arg-type]

            response = loop.handle_message(InboundMessage(text="hello"))

        self.assertFalse(response.ok)
        self.assertEqual(response.error_type, "RuntimeError")


if __name__ == "__main__":
    unittest.main()
