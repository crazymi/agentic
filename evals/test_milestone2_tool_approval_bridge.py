from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.channels.ntfy import NtfyChannel, NtfyConfig
from agentic.policy import PolicyEngine
from agentic.runtime.approval_bridge import ApprovalToolBridge
from agentic.runtime.tool_bridge import ToolBridge
from agentic.traces.logger import TraceLogger


class Milestone2ToolApprovalBridgeTests(unittest.TestCase):
    def test_allowed_tool_still_executes(self) -> None:
        with _bridge() as bridge:
            result = bridge.execute_tool_call_text(
                '{"tool":"add","arguments":{"a":1,"b":1}}'
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.result, 2)

    def test_unknown_sensitive_tool_creates_approval_without_execution(self) -> None:
        with _bridge() as bridge:
            result = bridge.execute_tool_call_text(
                '{"tool":"shell","arguments":{"cmd":"date"}}'
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.error_type, "approval_required")
            self.assertTrue(result.approval_id)

    def test_approval_request_can_send_ntfy_notification(self) -> None:
        calls = []
        ntfy = NtfyChannel(
            NtfyConfig(enabled=True, topic="topic"),
            transport=lambda url, data, headers: calls.append((url, data, headers)) or 200,
        )
        with _bridge(ntfy=ntfy) as bridge:
            result = bridge.execute_tool_call_text(
                '{"tool":"shell","arguments":{"cmd":"date"}}'
            )

            event_types = [event.event_type for event in bridge.trace.read_events()]

        self.assertEqual(result.error_type, "approval_required")
        self.assertEqual(len(calls), 1)
        self.assertIn("approval_notification_sent", event_types)

    def test_denied_policy_blocks_without_approval(self) -> None:
        with _bridge() as bridge:
            result = bridge.execute_tool_call_text(
                '{"tool":"credential_exfiltration","arguments":{}}'
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.error_type, "policy_denied")
            self.assertIsNone(result.approval_id)

    def test_approved_request_can_execute_later(self) -> None:
        with _bridge() as bridge:
            pending = bridge.execute_tool_call_text(
                '{"tool":"new_external_action","arguments":{}}'
            )

            executed = bridge.execute_approved(pending.approval_id or "")

            self.assertFalse(executed.ok)
            self.assertEqual(executed.error_type, "approval_not_approved")

    def test_approved_request_executes_original_tool_call(self) -> None:
        with _bridge() as bridge:
            request = bridge.approvals.create_request(
                capability="tool:add",
                reason="manual approval fixture",
                payload={"tool_call_text": '{"tool":"add","arguments":{"a":2,"b":3}}'},
            )
            bridge.approvals.approve(request.approval_id)

            executed = bridge.execute_approved(request.approval_id)

            self.assertTrue(executed.ok)
            self.assertEqual(executed.result, 5)


class _bridge:
    def __init__(self, ntfy: NtfyChannel | None = None):
        self.ntfy = ntfy

    def __enter__(self) -> ApprovalToolBridge:
        self.tmpdir = tempfile.TemporaryDirectory()
        path = Path(self.tmpdir.name)
        trace = TraceLogger(path / "trace.jsonl")
        bridge = ApprovalToolBridge(
            tool_bridge=ToolBridge(trace=trace),
            policy=PolicyEngine(),
            approvals=ApprovalService(ApprovalStore(path / "approvals.jsonl"), trace=trace),
            trace=trace,
            ntfy=self.ntfy,
        )
        bridge.trace = trace
        return bridge

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
