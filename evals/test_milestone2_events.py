from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.runtime.events import InboundMessage, RuntimeEvent, record_channel_message
from agentic.traces.logger import TraceLogger


class Milestone2EventTests(unittest.TestCase):
    def test_inbound_message_creates_traceable_event(self) -> None:
        message = InboundMessage(text="hello", channel="web")
        event = message.to_event()

        self.assertIsInstance(event, RuntimeEvent)
        self.assertTrue(event.event_id)
        self.assertEqual(event.event_type, "channel_message_received")
        self.assertEqual(event.payload["text"], "hello")

    def test_payload_must_be_json_compatible(self) -> None:
        with self.assertRaises(ValueError):
            RuntimeEvent(
                event_type="bad",
                source="test",
                payload={"not_json": object()},
            )

    def test_record_channel_message_writes_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            record_channel_message(trace, InboundMessage(text="hi"))
            events = trace.read_events()

        self.assertEqual(events[0].event_type, "channel_message_received")
        self.assertEqual(events[0].payload["text"], "hi")


if __name__ == "__main__":
    unittest.main()
