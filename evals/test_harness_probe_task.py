from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic.config.settings import load_app_config
from agentic.probes import (
    WORKFLOW_BUILDER_PROBE_TASK_KIND,
    WORKFLOW_SPEC_PROBE_TASK_KIND,
    WorkflowBuilderProbeExecutor,
    WorkflowSpecProbeExecutor,
)
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.task_router import TaskRouter
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import DurableTaskStatus, TaskRecord
from agentic.tasks.store import TaskStore


class EchoExecutor:
    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        return {"kind": task.kind, "value": task.input.get("value")}


class ProbeResult:
    ok = True
    blocker = ""

    def to_record(self) -> dict:
        return {
            "ok": True,
            "new_proposals": [{"proposal_id": "skp_real_boundary"}],
        }


class WorkflowSpecProbeResult:
    ok = True
    blocker = ""

    def to_record(self) -> dict:
        return {
            "ok": True,
            "new_workflows": [{"workflow_id": "wf_real_boundary"}],
        }


class HarnessProbeTaskTests(unittest.TestCase):
    def test_task_router_dispatches_by_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "agentic.sqlite3")
            task = store.create_task(kind="echo", input={"value": "hello"})
            router = TaskRouter({"echo": EchoExecutor()})

            result = router.execute(task, TaskExecutionContext(store))

        self.assertEqual(result, {"kind": "echo", "value": "hello"})

    def test_workflow_builder_probe_executor_runs_as_durable_task(self) -> None:
        config = load_app_config("config/config.toml")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            store = TaskStore(state_dir / "agentic.sqlite3")
            task = store.create_task(
                kind=WORKFLOW_BUILDER_PROBE_TASK_KIND,
                input={
                    "request": "반복 자동화 워크플로우 만들어줘",
                    "answers": ["source", "cadence"],
                    "state_dir": str(state_dir),
                },
            )
            pool = TaskPool(
                store=store,
                executor=TaskRouter(
                    {
                        WORKFLOW_BUILDER_PROBE_TASK_KIND: WorkflowBuilderProbeExecutor(
                            config=config,
                            state_dir=state_dir,
                        )
                    }
                ),
                max_workers=1,
            )

            with patch(
                "agentic.probes.task_executor.run_workflow_builder_probe",
                return_value=ProbeResult(),
            ) as runner:
                try:
                    pool.kick()
                    completed = _wait_for_completed(store, task.task_id)
                finally:
                    pool.shutdown()

        self.assertEqual(completed.status, DurableTaskStatus.COMPLETED)
        self.assertEqual(completed.result["new_proposals"][0]["proposal_id"], "skp_real_boundary")
        runner.assert_called_once()

    def test_workflow_spec_probe_executor_runs_as_durable_task(self) -> None:
        config = load_app_config("config/config.toml")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            store = TaskStore(state_dir / "agentic.sqlite3")
            task = store.create_task(
                kind=WORKFLOW_SPEC_PROBE_TASK_KIND,
                input={
                    "request": "반복 자동화 WorkflowSpec 만들어줘",
                    "answers": ["source", "cadence"],
                    "state_dir": str(state_dir),
                },
            )
            pool = TaskPool(
                store=store,
                executor=TaskRouter(
                    {
                        WORKFLOW_SPEC_PROBE_TASK_KIND: WorkflowSpecProbeExecutor(
                            config=config,
                            state_dir=state_dir,
                        )
                    }
                ),
                max_workers=1,
            )

            with patch(
                "agentic.probes.task_executor.run_workflow_spec_probe",
                return_value=WorkflowSpecProbeResult(),
            ) as runner:
                try:
                    pool.kick()
                    completed = _wait_for_completed(store, task.task_id)
                finally:
                    pool.shutdown()

        self.assertEqual(completed.status, DurableTaskStatus.COMPLETED)
        self.assertEqual(completed.result["new_workflows"][0]["workflow_id"], "wf_real_boundary")
        runner.assert_called_once()

    def test_unknown_task_kind_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "agentic.sqlite3")
            task = store.create_task(kind="missing", input={})
            router = TaskRouter({})

            with self.assertRaisesRegex(ValueError, "no executor registered"):
                router.execute(task, TaskExecutionContext(store))


def _wait_for_completed(store: TaskStore, task_id: str) -> TaskRecord:
    import time

    deadline = time.time() + 5
    while time.time() < deadline:
        task = store.get_task(task_id)
        if task.status in {DurableTaskStatus.COMPLETED, DurableTaskStatus.FAILED}:
            return task
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not finish")


if __name__ == "__main__":
    unittest.main()
