from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactRecord, ArtifactStatus, ArtifactStore
from agentic.ops import HealthMonitor, RuntimeHealthStatus
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceStore
from agentic.tasks.state_machine import DurableTaskStatus
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel import WorkflowStore


class Milestone10OpsHealthTests(unittest.TestCase):
    def test_health_snapshot_reports_operational_counts_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_store = TaskStore(root / "tasks.sqlite3")
            failed = task_store.create_task(kind="chat_turn", input={"message": "x"})
            task_store.transition(
                failed.task_id,
                DurableTaskStatus.FAILED,
                error={"type": "RuntimeError", "message": "boom"},
            )
            source_store = SourceStore(root / "sources.sqlite3")
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Missing source",
                    locator=str(root / "missing.jsonl"),
                    enabled=True,
                )
            )
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    name="needs review",
                    kind="script",
                    content="print('review')",
                    status=ArtifactStatus.REVIEW_REQUIRED,
                )
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            approvals.create_request(capability="tool:shell", reason="test", payload={"cmd": "date"})
            monitor = HealthMonitor(
                task_store=task_store,
                workflow_store=WorkflowStore(root / "workflows.sqlite3"),
                source_store=source_store,
                artifact_store=artifact_store,
                approvals=approvals,
            )

            snapshot = monitor.snapshot().to_record()

        self.assertEqual(snapshot["status"], RuntimeHealthStatus.UNHEALTHY)
        self.assertEqual(snapshot["counters"]["tasks"]["failed"], 1)
        self.assertEqual(snapshot["counters"]["approvals"]["pending"], 1)
        self.assertEqual(snapshot["counters"]["artifacts"]["review_required"], 1)
        self.assertTrue(snapshot["warnings"])
        self.assertEqual(snapshot["recent_failures"][0]["id"], failed.task_id)

    def test_health_snapshot_exports_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            monitor = HealthMonitor(task_store=TaskStore(root / "tasks.sqlite3"))
            target = root / "status" / "health.json"

            snapshot = monitor.export_snapshot(target)
            loaded = json.loads(target.read_text(encoding="utf-8"))

        self.assertEqual(loaded["status"], snapshot.status)
        self.assertTrue(loaded["generated_at"])

    def test_web_ops_health_route_and_export_button(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = TraceLogger(root / "trace.jsonl")
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"), trace)
            monitor = HealthMonitor(
                task_store=TaskStore(root / "tasks.sqlite3"),
                workflow_store=WorkflowStore(root / "workflows.sqlite3"),
                source_store=SourceStore(root / "sources.sqlite3"),
                artifact_store=ArtifactStore(root / "artifacts.sqlite3"),
                approvals=approvals,
            )
            export_path = root / "health_snapshot.json"
            app = create_app(
                channel_loop=None,
                approvals=approvals,
                trace=trace,
                task_store=monitor.task_store,
                workflow_store=monitor.workflow_store,
                health_monitor=monitor,
                health_export_path=export_path,
            )

            health = _request(app, "GET", "/ops/health").json()
            page = _request(app, "GET", "/").text
            response = _request(app, "POST", "/ops/health/export")
            exported = export_path.exists()

        self.assertEqual(health["status"], RuntimeHealthStatus.DEGRADED)
        self.assertIn("Ops Health", page)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(exported)


class AsgiResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.text = body.decode("utf-8")

    def json(self):
        return json.loads(self.text)


def _request(app, method: str, path: str) -> AsgiResponse:
    import asyncio

    async def run() -> AsgiResponse:
        sent_request = False
        status_code = 0
        body_parts: list[bytes] = []

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [(b"host", b"testserver")],
                "client": ("127.0.0.1", 123),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        return AsgiResponse(status_code, b"".join(body_parts))

    return asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
