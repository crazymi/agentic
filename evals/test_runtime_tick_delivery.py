from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactRecord, ArtifactStore
from agentic.delivery import DeliveryStore, ReportDeliveryService
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.tick import RuntimeTickService
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import TaskRecord
from agentic.tasks.store import TaskStore


class FakeNtfy:
    def __init__(self):
        self.messages: list[dict] = []

    def send_text(self, *, title: str, body: str, tags: str = "") -> bool:
        self.messages.append({"title": title, "body": body, "tags": tags})
        return True


class ReportTaskExecutor:
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        artifact = self.artifact_store.create(
            ArtifactRecord(
                kind=ArtifactKind.REPORT,
                name="Task report",
                content=_quality_report_body(task.task_id),
            )
        )
        return {"ok": True, "artifact_id": artifact.artifact_id}


class RuntimeTickDeliveryTests(unittest.TestCase):
    def test_tick_runs_queued_task_then_delivers_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            task_store = TaskStore(root / "agentic.sqlite3")
            task_store.create_task(kind="report_task", input={})
            ntfy = FakeNtfy()
            pool = TaskPool(
                store=task_store,
                executor=ReportTaskExecutor(artifact_store),
                max_workers=1,
                heartbeat_interval_s=0,
            )
            tick = RuntimeTickService(
                task_pool=pool,
                report_delivery=ReportDeliveryService(
                    artifact_store=artifact_store,
                    delivery_store=DeliveryStore(root / "deliveries.sqlite3"),
                    ntfy_channel=ntfy,
                ),
            )
            try:
                result = tick.run_once(timeout_s=5)
            finally:
                pool.shutdown(wait=True)

            self.assertTrue(result.ok)
            self.assertEqual(result.tasks_submitted, 1)
            self.assertEqual(len(result.delivery.sent), 1)
            self.assertIn("Executive Summary", ntfy.messages[0]["body"])


def _quality_report_body(task_id: str) -> str:
    return f"""# Task report

Goal: verify runtime delivery for {task_id}

## Executive Summary

- Analyzed 3 item(s) for a runtime-delivered report.
- Top themes: task, report, delivery
- Evidence window: 3 item(s)

## Evidence

- [1] Runtime task started | The queued task produced a report artifact | task://{task_id}/1
- [2] Runtime task completed | The worker stored a useful artifact | task://{task_id}/2
- [3] Delivery gate evaluated | The report was checked before notification | task://{task_id}/3

## Signals

- Runtime task started :: queued work can create artifacts.
- Runtime task completed :: completed workers persist result state.
- Delivery gate evaluated :: reports pass quality admission before notification.

## Source Quality

- source=runtime_task ok=True score=100 items=3 reasons=

## Next Watch Points

- Watch failed deliveries for retry behavior.
- Watch queued tasks for stale heartbeat.
- Watch report quality before sending owner notifications.
"""


if __name__ == "__main__":
    unittest.main()
