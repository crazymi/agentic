from __future__ import annotations

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.runtime.daemon import recover_interrupted_tasks
from agentic.runtime.durable_channel_loop import DurableChannelLoop
from agentic.runtime.task_control import TaskControl
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


class FakeChatExecutor:
    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        message = task.input.get("message", "")
        answer = "2" if "1+1" in message else f"echo: {message}"
        return {"ok": True, "final_answer": answer}


class Milestone3FullFlowTests(unittest.TestCase):
    def test_web_message_enqueues_worker_completes_and_ui_shows_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = TraceLogger(root / "trace.jsonl")
            store = TaskStore(root / "state.sqlite3")
            pool = TaskPool(store=store, executor=FakeChatExecutor(), max_workers=1)
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"), trace)
            loop = DurableChannelLoop(store=store, pool=pool, trace=trace)
            app = create_app(
                channel_loop=None,
                durable_channel_loop=loop,
                approvals=approvals,
                trace=trace,
                task_store=store,
                task_control=TaskControl(store),
            )
            try:
                response = _request(
                    app,
                    "POST",
                    "/messages",
                    data={"message": "1+1은 뭐지?"},
                )
                task = store.list_tasks(kind="chat_turn")[0]
                _wait_for_status(store, task.task_id, DurableTaskStatus.COMPLETED)
                home = _request(app, "GET", "/")
                completed = store.get_task(task.task_id)
            finally:
                pool.shutdown()

        self.assertEqual(response.status_code, 303)
        self.assertEqual(completed.result["final_answer"], "2")
        self.assertIn("2", home.text)

    def test_restart_marks_running_task_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "state.sqlite3")
            task = store.create_task(kind="fake", input={})
            store.transition(task.task_id, DurableTaskStatus.RUNNING)

            recovered = recover_interrupted_tasks(TaskStore(Path(tmpdir) / "state.sqlite3"))
            latest = store.get_task(task.task_id)

        self.assertEqual(recovered, [task.task_id])
        self.assertEqual(latest.status, DurableTaskStatus.UNHEALTHY)


def _wait_for_status(store: TaskStore, task_id: str, status: DurableTaskStatus) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if store.get_task(task_id).status == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not reach {status}")


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
