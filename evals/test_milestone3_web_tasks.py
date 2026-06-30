from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.runtime.task_control import TaskControl
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


class Milestone3WebTaskTests(unittest.TestCase):
    def test_home_and_tasks_route_render_task_status(self) -> None:
        with _fixture() as fixture:
            fixture.store.create_task(kind="chat_turn", input={"message": "hi"})

            home = _request(fixture.app, "GET", "/")
            tasks = _request(fixture.app, "GET", "/tasks")

        self.assertEqual(home.status_code, 200)
        self.assertIn("Tasks", home.text)
        self.assertIn("queued", home.text)
        self.assertEqual(tasks.status_code, 200)
        self.assertIn("chat_turn", tasks.text)

    def test_task_detail_route(self) -> None:
        with _fixture() as fixture:
            task = fixture.store.create_task(kind="chat_turn", input={"message": "hi"})

            response = _request(fixture.app, "GET", f"/tasks/{task.task_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(task.task_id, response.text)

    def test_cancel_pause_resume_routes(self) -> None:
        with _fixture() as fixture:
            cancel_task = fixture.store.create_task(kind="chat_turn", input={})
            pause_task = fixture.store.create_task(kind="chat_turn", input={})

            cancel_response = _request(
                fixture.app, "POST", f"/tasks/{cancel_task.task_id}/cancel"
            )
            pause_response = _request(
                fixture.app, "POST", f"/tasks/{pause_task.task_id}/pause"
            )
            resume_response = _request(
                fixture.app, "POST", f"/tasks/{pause_task.task_id}/resume"
            )

            cancelled = fixture.store.get_task(cancel_task.task_id)
            resumed = fixture.store.get_task(pause_task.task_id)

        self.assertEqual(cancel_response.status_code, 303)
        self.assertEqual(pause_response.status_code, 303)
        self.assertEqual(resume_response.status_code, 303)
        self.assertEqual(cancelled.status, DurableTaskStatus.CANCELLED)
        self.assertEqual(resumed.status, DurableTaskStatus.QUEUED)


class _fixture:
    def __enter__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.trace = TraceLogger(root / "trace.jsonl")
        self.store = TaskStore(root / "state.sqlite3")
        approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"), self.trace)
        self.app = create_app(
            channel_loop=None,
            durable_channel_loop=None,
            approvals=approvals,
            trace=self.trace,
            task_store=self.store,
            task_control=TaskControl(self.store),
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmpdir.cleanup()


class AsgiResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.text = body.decode("utf-8")


def _request(app, method: str, path: str, data: dict[str, str] | None = None) -> AsgiResponse:
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
