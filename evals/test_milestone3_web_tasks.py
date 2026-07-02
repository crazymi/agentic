from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.delivery import DeliveryRecord, DeliveryStore
from agentic.probes import WORKFLOW_BUILDER_PROBE_TASK_KIND
from agentic.runtime.durable_channel_loop import DurableChannelLoop
from agentic.runtime.task_control import TaskControl
from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore
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

    def test_workflow_builder_probe_route_enqueues_task(self) -> None:
        with _fixture(with_durable=True) as fixture:
            response = _request(
                fixture.app,
                "POST",
                "/probes/workflow-builder",
                data={
                    "request": "반복 자동화 워크플로우 만들어줘",
                    "answers": "source\ncadence",
                },
            )
            tasks = fixture.store.list_tasks(kind=WORKFLOW_BUILDER_PROBE_TASK_KIND)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].input["answers"], ["source", "cadence"])
        self.assertEqual(fixture.pool.kicks, 1)

    def test_delivery_and_daemon_status_render(self) -> None:
        with _fixture(with_delivery=True, with_daemon=True) as fixture:
            delivery = fixture.delivery_store.create(
                DeliveryRecord(
                    artifact_id="art_1",
                    channel="ntfy",
                    title="Report",
                    body="Report body",
                )
            )

            home = _request(fixture.app, "GET", "/")
            deliveries = _request(fixture.app, "GET", "/deliveries")
            daemon = _request(fixture.app, "GET", "/daemon")

        self.assertEqual(home.status_code, 200)
        self.assertIn("Runtime Daemon", home.text)
        self.assertIn("Deliveries", home.text)
        self.assertIn(delivery.delivery_id, home.text)
        self.assertEqual(deliveries.status_code, 200)
        self.assertIn(delivery.delivery_id, deliveries.text)
        self.assertEqual(daemon.status_code, 200)
        self.assertIn("tick_count", daemon.text)

    def test_skill_proposal_apply_routes_use_approval_gate(self) -> None:
        with _fixture(with_skill_workshop=True) as fixture:
            proposal = fixture.skill_workshop.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Workflow Building\n\nAsk one question.",
            )

            request_response = _request(
                fixture.app,
                "POST",
                f"/skills/proposals/{proposal.proposal_id}/request-apply",
            )
            pending = fixture.approvals.get_pending()[0]
            fixture.approvals.approve(pending.approval_id)
            apply_response = _request(
                fixture.app,
                "POST",
                f"/skills/proposals/{proposal.proposal_id}/apply",
                data={"approval_id": pending.approval_id},
            )
            applied = fixture.skill_workshop.inspect(proposal.proposal_id)
            skill_file_exists = (
                fixture.root / "skills" / "workflow-building" / "SKILL.md"
            ).exists()

        self.assertEqual(request_response.status_code, 303)
        self.assertEqual(apply_response.status_code, 303)
        self.assertEqual(applied.status.value, "applied")
        self.assertTrue(skill_file_exists)


class _fixture:
    def __init__(
        self,
        *,
        with_durable: bool = False,
        with_skill_workshop: bool = False,
        with_delivery: bool = False,
        with_daemon: bool = False,
    ):
        self.with_durable = with_durable
        self.with_skill_workshop = with_skill_workshop
        self.with_delivery = with_delivery
        self.with_daemon = with_daemon

    def __enter__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        root = self.root
        self.trace = TraceLogger(root / "trace.jsonl")
        self.store = TaskStore(root / "state.sqlite3")
        self.pool = RecordingPool()
        durable_channel_loop = (
            DurableChannelLoop(store=self.store, pool=self.pool, trace=self.trace)
            if self.with_durable
            else None
        )
        self.approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"), self.trace)
        self.skill_workshop = (
            SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            if self.with_skill_workshop
            else None
        )
        self.delivery_store = DeliveryStore(root / "deliveries.sqlite3") if self.with_delivery else None
        self.daemon = RecordingDaemon() if self.with_daemon else None
        self.app = create_app(
            channel_loop=None,
            durable_channel_loop=durable_channel_loop,
            approvals=self.approvals,
            trace=self.trace,
            task_store=self.store,
            task_control=TaskControl(self.store),
            skill_workshop=self.skill_workshop,
            delivery_store=self.delivery_store,
            runtime_daemon=self.daemon,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.tmpdir.cleanup()


class RecordingPool:
    def __init__(self):
        self.kicks = 0

    def kick(self) -> int:
        self.kicks += 1
        return 0


class RecordingDaemon:
    def __init__(self):
        self.ticks = 0

    def snapshot(self):
        return {
            "running": True,
            "tick_count": self.ticks,
            "last_tick_at": "now",
            "last_result": {"ok": True},
        }

    def run_once(self):
        self.ticks += 1
        return RuntimeTickLike()


class RuntimeTickLike:
    def to_record(self):
        return {"ok": True}


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
