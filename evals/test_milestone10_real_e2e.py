from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.workflow_kernel import (
    IntentType,
    StepType,
    WorkflowBuilder,
    WorkflowInterpreter,
    WorkflowStatus,
    WorkflowStore,
)
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep


class Milestone10RealEndToEndTests(unittest.TestCase):
    def test_real_local_source_workflow_collects_aggregates_analyzes_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "community_posts.jsonl"
            source_file.write_text(
                "\n".join(
                    [
                        '{"uri":"community://post-1","title":"AI capex watch","content_text":"AI automation demand and inference chips are the main debate today."}',
                        '{"uri":"community://post-2","title":"Browser agent reliability","content_text":"Browser automation is exciting, but reliability and approval gates matter."}',
                        '{"uri":"community://post-3","title":"Small cap risk appetite","content_text":"Traders discuss rate cuts, AI infrastructure, and startup ideas."}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.FEED,
                    name="Community trend feed",
                    locator=source_file.as_uri(),
                    enabled=True,
                )
            )
            spec = workflow_store.create_spec(_trend_workflow(source.source_id))
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)
            builder = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=source_runtime,
                    resource_store=resource_store,
                )
            )

            result = builder.run_approved(spec, trigger={"type": "manual_e2e"})
            report_artifacts = [
                artifact
                for artifact in artifact_store.list(run_id=result.run.run_id)
                if artifact.kind == ArtifactKind.REPORT
            ]
            resources = resource_store.search("automation", limit=10)

        self.assertTrue(result.ok)
        self.assertEqual(result.run.status.value, "completed")
        self.assertEqual(result.run.step_results["collect"]["collected_count"], 3)
        self.assertEqual(result.run.step_results["collect"]["new_count"], 3)
        self.assertEqual(len(result.run.step_results["collect"]["resource_ids"]), 3)
        self.assertEqual(len(result.run.step_results["collect"]["recent_resource_ids"]), 3)
        self.assertEqual(len(result.run.step_results["collect"]["analysis_resource_ids"]), 3)
        self.assertGreaterEqual(result.run.step_results["aggregate"]["keyword_counts"]["ai"], 2)
        self.assertEqual(len(resources), 2)
        self.assertEqual(len(report_artifacts), 1)
        self.assertIn("Analyzed 3 item(s)", report_artifacts[0].content)

    def test_recurring_collect_analyzes_recent_resources_when_no_new_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "community_posts.jsonl"
            source_file.write_text(
                "\n".join(
                    [
                        '{"uri":"community://post-1","title":"AI capex watch","content_text":"AI automation demand and inference chips are the main debate today."}',
                        '{"uri":"community://post-2","title":"Browser agent reliability","content_text":"Browser automation is exciting, but reliability and approval gates matter."}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.FEED,
                    name="Community trend feed",
                    locator=source_file.as_uri(),
                    enabled=True,
                )
            )
            spec = workflow_store.create_spec(_trend_workflow(source.source_id))
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)
            builder = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=SourceRuntime(source_store=source_store, resource_store=resource_store),
                    resource_store=resource_store,
                )
            )

            first = builder.run_approved(spec, trigger={"type": "manual_e2e"})
            second = builder.run_approved(spec, trigger={"type": "manual_e2e"})

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(second.run.step_results["collect"]["new_count"], 0)
        self.assertEqual(second.run.step_results["analyze"]["summary"].split()[1], "2")


def _trend_workflow(source_id: str) -> WorkflowSpec:
    return WorkflowSpec(
        name="Real Local Social Trend E2E",
        description="M10 real-only local source workflow check.",
        goal="Collect community posts, aggregate recurring terms, analyze the trend, and write a report.",
        success_criteria=[
            "Read actual local JSONL source records",
            "Persist collected resources",
            "Aggregate keyword counts",
            "Create a report artifact",
        ],
        owner_channel="web",
        intent_type=IntentType.SCHEDULED_WORKFLOW,
        triggers=[{"type": "manual"}],
        inputs={"source_id": source_id},
        sources=[{"source_id": source_id, "kind": SourceKind.FEED.value}],
        steps=[
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect community posts",
                config={"source": SourceKind.FEED.value, "source_id": source_id},
            ),
            WorkflowStep(
                step_id="aggregate",
                step_type=StepType.AGGREGATE,
                name="Aggregate keyword counts",
                depends_on=["collect"],
            ),
            WorkflowStep(
                step_id="analyze",
                step_type=StepType.ANALYZE,
                name="Analyze trend signals",
                config={"goal": "Identify AI, automation, and market-risk signals."},
                depends_on=["aggregate"],
            ),
            WorkflowStep(
                step_id="report",
                step_type=StepType.REPORT,
                name="Render trend report",
                config={"output": "trend_report"},
                depends_on=["analyze"],
            ),
        ],
        capabilities=[{"capability": f"source:{SourceKind.FEED.value}:read", "risk": "low"}],
        policy={"production_external_source": False},
        outputs=[{"type": "report", "channel": "web"}],
        evals=[{"type": "real_local_e2e", "required": True}],
        assumptions=["The source is a real local JSONL file, not generated by the workflow runtime."],
    )


if __name__ == "__main__":
    unittest.main()
