from __future__ import annotations

import unittest

from agentic.approvals.models import ApprovalRequest
from agentic.channels.ntfy import NtfyChannel, NtfyConfig


class Milestone2NtfyChannelTests(unittest.TestCase):
    def test_disabled_channel_does_not_send(self) -> None:
        calls = []
        channel = NtfyChannel(
            NtfyConfig(enabled=False, topic="topic"),
            transport=lambda url, data, headers: calls.append((url, data, headers)) or 200,
        )

        sent = channel.send_approval_request(_approval())

        self.assertFalse(sent)
        self.assertEqual(calls, [])

    def test_enabled_channel_uses_injected_transport(self) -> None:
        calls = []
        channel = NtfyChannel(
            NtfyConfig(enabled=True, topic="topic", web_url="http://local"),
            transport=lambda url, data, headers: calls.append((url, data, headers)) or 200,
        )

        sent = channel.send_approval_request(_approval())

        self.assertTrue(sent)
        self.assertEqual(calls[0][0], "https://ntfy.sh/topic")
        self.assertIn(b"tool:shell", calls[0][1])


def _approval() -> ApprovalRequest:
    return ApprovalRequest(capability="tool:shell", reason="needs approval", payload={})


if __name__ == "__main__":
    unittest.main()
