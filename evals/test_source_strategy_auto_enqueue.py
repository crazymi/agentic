from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.sources.strategy_recovery import (
    SOURCE_STRATEGY_RECOVERY_TASK_KIND,
    SourceStrategyRecoveryEnqueuer,
)
from agentic.tasks.store import TaskStore
from agentic.tooling import ToolingBacklogStore
from agentic.workflow_kernel import StepType, WorkflowBuilder, WorkflowInterpreter, WorkflowStatus, WorkflowStore
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep


class SourceStrategyAutoEnqueueTests(unittest.TestCase):
    def test_quality_failure_enqueues_durable_recovery_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "nav.jsonl"
            source_file.write_text(
                "\n".join(
                    [
                        '{"uri":"https://old.reddit.com/#content","title":"jump to content","content_text":"jump to content"}',
                        '{"uri":"https://old.reddit.com/login","title":"log in","content_text":"log in"}',
                        '{"uri":"https://old.reddit.com/r/worldnews/","title":"worldnews","content_text":"worldnews"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            task_store = TaskStore(root / "agentic.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Navigation noise",
                    locator=source_file.as_uri(),
                    enabled=True,
                    metadata={"quality": {"min_score": 70, "min_items": 3}},
                )
            )
            spec = workflow_store.create_spec(_workflow(source.source_id))
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)

            result = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=SourceRuntime(source_store=source_store, resource_store=resource_store),
                    resource_store=resource_store,
                    tooling_store=tooling_store,
                    source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                        task_store=task_store,
                        state_dir=root,
                    ),
                )
            ).run_approved(spec)
            tasks = task_store.list_tasks(kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND)
            events = workflow_store.list_events(workflow_id=spec.workflow_id, limit=100)
            tooling = tooling_store.list(workflow_id=spec.workflow_id)

        self.assertFalse(result.ok)
        self.assertEqual(len(tooling), 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].status.value, "queued")
        self.assertEqual(tasks[0].input["tooling_id"], tooling[0].tooling_id)
        self.assertEqual(tasks[0].input["state_dir"], str(root))
        self.assertIn("workflow_source_strategy_recovery_enqueued", [event["event_type"] for event in events])


def _workflow(source_id: str) -> WorkflowSpec:
    return WorkflowSpec(
        name="Auto recovery enqueue workflow",
        goal="Fail quality gate and enqueue recovery.",
        status=WorkflowStatus.PROPOSED,
        triggers=[{"type": "manual"}],
        sources=[{"source_id": source_id, "kind": SourceKind.LOCAL_FILE.value}],
        outputs=[{"kind": "report"}],
        success_criteria=["Quality failure creates recovery task."],
        steps=[
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect",
                config={"source": SourceKind.LOCAL_FILE.value, "source_id": source_id},
            ),
            WorkflowStep(step_id="analyze", step_type=StepType.ANALYZE, name="Analyze"),
            WorkflowStep(step_id="report", step_type=StepType.REPORT, name="Report"),
        ],
    )


if __name__ == "__main__":
    unittest.main()
