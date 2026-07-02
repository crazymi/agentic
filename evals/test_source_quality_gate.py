from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import (
    SourceDefinition,
    SourceItem,
    SourceKind,
    SourceRuntime,
    SourceStore,
    evaluate_source_quality,
)
from agentic.workflow_kernel import (
    StepType,
    WorkflowBuilder,
    WorkflowInterpreter,
    WorkflowStatus,
    WorkflowStore,
)
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep
from agentic.tooling import ToolingBacklogStore


class SourceQualityGateTests(unittest.TestCase):
    def test_quality_report_flags_navigation_heavy_items(self) -> None:
        items = [
            SourceItem(source_id="src", uri="https://old.reddit.com/#content", title="jump to content", content_text="jump to content"),
            SourceItem(source_id="src", uri="https://old.reddit.com/r/worldnews/", title="worldnews", content_text="worldnews"),
            SourceItem(source_id="src", uri="https://old.reddit.com/login", title="log in", content_text="log in"),
            SourceItem(source_id="src", uri="https://old.reddit.com/r/stocks/comments/1", title="AI capex debate", content_text="AI capex debate"),
        ]

        report = evaluate_source_quality(items, source_url="https://old.reddit.com/r/stocks/new/", min_score=70)

        self.assertFalse(report.ok)
        self.assertIn("score_below_threshold", report.reasons)
        self.assertGreaterEqual(report.nav_like_count, 2)
        self.assertGreater(report.off_path_count, 0)

    def test_quality_report_allows_meaningful_items(self) -> None:
        items = [
            SourceItem(source_id="src", uri="local://1", title="AI capex debate", content_text="AI inference chip demand discussion"),
            SourceItem(source_id="src", uri="local://2", title="Browser agent reliability", content_text="Approval gates and retry evidence matter"),
            SourceItem(source_id="src", uri="local://3", title="Small cap risk appetite", content_text="Traders discuss rate cuts and AI infrastructure"),
        ]

        report = evaluate_source_quality(items, min_score=70, min_items=3)

        self.assertTrue(report.ok)
        self.assertGreaterEqual(report.score, 70)
        self.assertEqual(report.reasons, [])

    def test_quality_report_flags_query_identity_drift(self) -> None:
        items = [
            SourceItem(
                source_id="src",
                uri="https://gall.dcinside.com/board/view/?id=dcbest&no=1",
                title="인기글로 새어 나간 링크",
                content_text="인기글로 새어 나간 링크",
            ),
            SourceItem(
                source_id="src",
                uri="https://gall.dcinside.com/board/view/?id=dcbest&no=2",
                title="다른 게시판 링크",
                content_text="다른 게시판 링크",
            ),
            SourceItem(
                source_id="src",
                uri="https://gall.dcinside.com/board/view/?id=stock_new2&no=3",
                title="주식 관련 게시글",
                content_text="주식 관련 게시글",
            ),
        ]

        report = evaluate_source_quality(
            items,
            source_url="https://gall.dcinside.com/board/lists/?id=stock_new2",
            min_score=70,
            min_items=3,
        )

        self.assertFalse(report.ok)
        self.assertEqual(report.off_path_count, 2)
        self.assertIn("off_source_path_items", report.reasons)

    def test_quality_report_flags_notice_and_bracket_noise(self) -> None:
        items = [
            SourceItem(source_id="src", uri="https://example.test/1", title="정치, 사회 갤러리 이용 안내", content_text="정치, 사회 갤러리 이용 안내"),
            SourceItem(source_id="src", uri="https://example.test/2", title="[1213]", content_text="[1213]"),
            SourceItem(source_id="src", uri="https://example.test/3", title="AI 반도체 수요", content_text="AI 반도체 수요"),
        ]

        report = evaluate_source_quality(items, min_score=70, min_items=3)

        self.assertFalse(report.ok)
        self.assertGreaterEqual(report.nav_like_count, 2)
        self.assertIn("navigation_like_items", report.reasons)

    def test_workflow_fails_before_report_when_source_quality_is_low(self) -> None:
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
                )
            ).run_approved(spec)
            reports = artifact_store.list(run_id=result.run.run_id)
            events = workflow_store.list_events(run_id=result.run.run_id)
            tooling = tooling_store.list(workflow_id=spec.workflow_id)

        self.assertFalse(result.ok)
        self.assertEqual(result.run.status.value, "failed")
        self.assertEqual(result.run.error["type"], "SourceQualityError")
        self.assertIn("reports", result.run.error)
        self.assertEqual([artifact.kind for artifact in reports if artifact.kind == ArtifactKind.REPORT], [])
        self.assertIn("workflow_source_quality_failed", [event["event_type"] for event in events])
        self.assertIn("workflow_source_strategy_tuning_requested", [event["event_type"] for event in events])
        self.assertEqual(len(tooling), 1)
        self.assertEqual(tooling[0].capability, "source:strategy_tuning")
        self.assertEqual(tooling[0].action, "revise_source_strategy")
        self.assertIn("quality_reports", tooling[0].payload)
        self.assertIn("agent_review_prompt", tooling[0].payload)
        self.assertIn("revise_extraction_filters", tooling[0].payload["candidate_actions"])


def _workflow(source_id: str) -> WorkflowSpec:
    return WorkflowSpec(
        name="Quality gated workflow",
        goal="Collect meaningful source items before reporting.",
        status=WorkflowStatus.PROPOSED,
        triggers=[{"type": "manual"}],
        sources=[{"source_id": source_id, "kind": SourceKind.LOCAL_FILE.value}],
        outputs=[{"kind": "report"}],
        success_criteria=["Report is created only from useful source items."],
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
