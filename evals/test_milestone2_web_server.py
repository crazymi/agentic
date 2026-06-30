from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.runtime.channel_loop import ChannelResponse
from agentic.traces.logger import TraceLogger


class FakeChannelLoop:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def handle_message(self, message) -> ChannelResponse:
        self.messages.append(message.text)
        return ChannelResponse(ok=True, text=f"echo: {message.text}")


class Milestone2WebServerTests(unittest.TestCase):
    def test_health_route(self) -> None:
        with _web_fixture() as fixture:
            response = _request(fixture.app, "GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '{"status":"ok"}')

    def test_home_renders_chat_and_approvals(self) -> None:
        with _web_fixture(with_approval=True) as fixture:
            response = _request(fixture.app, "GET", "/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Pending Approvals", response.text)
        self.assertIn("tool:shell", response.text)

    def test_post_message_invokes_channel_loop(self) -> None:
        with _web_fixture() as fixture:
            response = _request(
                fixture.app,
                "POST",
                "/messages",
                data={"message": "hello"},
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(fixture.loop.messages, ["hello"])

    def test_approval_buttons_update_pending_list(self) -> None:
        with _web_fixture(with_approval=True) as fixture:
            approval_id = fixture.service.get_pending()[0].approval_id

            response = _request(fixture.app, "POST", f"/approvals/{approval_id}/deny")

        self.assertEqual(response.status_code, 303)
        self.assertEqual(fixture.service.get_pending(), [])


class WebFixture:
    def __init__(self, with_approval: bool = False):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.trace = TraceLogger(Path(self.tmpdir.name) / "trace.jsonl")
        self.service = ApprovalService(
            ApprovalStore(Path(self.tmpdir.name) / "approvals.jsonl"),
            trace=self.trace,
        )
        if with_approval:
            self.service.create_request(
                capability="tool:shell",
                reason="needs approval",
                payload={},
            )
        self.loop = FakeChannelLoop()
        self.app = create_app(
            channel_loop=self.loop,  # type: ignore[arg-type]
            approvals=self.service,
            trace=self.trace,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmpdir.cleanup()


def _web_fixture(with_approval: bool = False) -> WebFixture:
    return WebFixture(with_approval=with_approval)


class AsgiResponse:
    def __init__(self, status_code: int, headers: list[tuple[bytes, bytes]], body: bytes):
        self.status_code = status_code
        self.headers = headers
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
        headers: list[tuple[bytes, bytes]] = []
        body_parts: list[bytes] = []

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code, headers
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        query = b""
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query,
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
        return AsgiResponse(status_code, headers, b"".join(body_parts))

    return asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
