from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.channels.ntfy import NtfyChannel, NtfyConfig
from agentic.policy import PolicyEngine
from agentic.runtime.approval_bridge import ApprovalToolBridge
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.tool_bridge import ToolBridge
from agentic.traces.logger import TraceLogger


class FakeFullLoopRuntime:
    def __init__(self, approval_bridge: ApprovalToolBridge, ntfy: NtfyChannel):
        self.approval_bridge = approval_bridge
        self.ntfy = ntfy

    def run_user_message(self, message: str):
        class Result:
            ok = True
            final_answer = "ok"
            error_type = None
            error_message = None

        if message == "sensitive":
            bridge_result = self.approval_bridge.execute_tool_call_text(
                '{"tool":"shell","arguments":{"cmd":"date"}}'
            )
            if bridge_result.approval_id:
                approval = self.approval_bridge.approvals.get(bridge_result.approval_id)
                self.ntfy.send_approval_request(approval)
            Result.ok = False
            Result.final_answer = bridge_result.error_message or ""
            Result.error_type = bridge_result.error_type
        return Result()


class Milestone2FullFlowTests(unittest.TestCase):
    def test_web_message_approval_ntfy_and_decision_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            trace = TraceLogger(path / "trace.jsonl")
            approvals = ApprovalService(ApprovalStore(path / "approvals.jsonl"), trace)
            approval_bridge = ApprovalToolBridge(
                tool_bridge=ToolBridge(trace=trace),
                policy=PolicyEngine(),
                approvals=approvals,
                trace=trace,
            )
            ntfy_calls = []
            ntfy = NtfyChannel(
                NtfyConfig(enabled=True, topic="topic"),
                transport=lambda url, data, headers: ntfy_calls.append(
                    (url, data, headers)
                )
                or 200,
            )
            channel_loop = ChannelLoop(
                runtime=FakeFullLoopRuntime(approval_bridge, ntfy),  # type: ignore[arg-type]
                trace=trace,
            )
            app = create_app(channel_loop=channel_loop, approvals=approvals, trace=trace)

            response = _request(
                app,
                "POST",
                "/messages",
                data={"message": "sensitive"},
            )
            pending = approvals.get_pending()
            deny_response = _request(
                app,
                "POST",
                f"/approvals/{pending[0].approval_id}/deny",
            )
            blocked = approval_bridge.execute_approved(pending[0].approval_id)
            events = [event.event_type for event in trace.read_events()]

        self.assertEqual(response.status_code, 303)
        self.assertEqual(deny_response.status_code, 303)
        self.assertEqual(len(ntfy_calls), 1)
        self.assertEqual(blocked.error_type, "approval_not_approved")
        self.assertIn("channel_message_received", events)
        self.assertIn("approval_requested", events)
        self.assertIn("tool_blocked_by_approval", events)
        self.assertIn("approval_decided", events)


class AsgiResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.text = body.decode("utf-8")


def _request(
    app,
    method: str,
    path: str,
    data: dict[str, str] | None = None,
) -> AsgiResponse:
    async def run() -> AsgiResponse:
        body = urlencode(data or {}).encode("utf-8")
        sent_request = False
        status_code = 0
        body_parts: list[bytes] = []

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
        return AsgiResponse(status_code, b"".join(body_parts))

    return asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
