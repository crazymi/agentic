from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.sources.discovery import (
    SOURCE_DISCOVERY_TASK_KIND,
    SourceCandidateStore,
    SourceDiscoveryEnqueuer,
    build_source_candidate_service,
)
from agentic.sources.store import SourceStore
from agentic.tasks.store import TaskStore
from agentic.workflow_kernel import StepType, WorkflowStatus, WorkflowStore
from agentic.workflow_kernel.lifecycle import WorkflowLifecycleService
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep


class SourceDiscoveryTests(unittest.TestCase):
    def test_source_candidate_tool_registers_public_web_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = build_source_candidate_service(root)
            result = service.propose(
                workflow_id="wf_test",
                requested_source="community_web",
                kind="web_page",
                name="Example community",
                locator="https://example.com/community",
                aliases=["example"],
                confidence=0.8,
                rationale="Chosen from a search result.",
                evidence=[{"title": "Example", "url": "https://example.com/community"}],
                auto_register=True,
            )
            sources = SourceStore(root / "sources.sqlite3").list_sources(enabled=True)
            candidates = SourceCandidateStore(root / "source_candidates.sqlite3").list()

        self.assertTrue(result["ok"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].status, "registered")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].locator, "https://example.com/community")
        self.assertIn("community_web", sources[0].metadata["aliases"])

    def test_lifecycle_missing_source_enqueues_source_discovery_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            task_store = TaskStore(root / "agentic.sqlite3")
            spec = workflow_store.create_spec(_missing_source_workflow())
            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=SourceStore(root / "sources.sqlite3"),
                source_discovery_enqueuer=SourceDiscoveryEnqueuer(
                    task_store=task_store,
                    state_dir=root,
                ),
            )
            result = service.advance_after_proposal(spec.workflow_id)
            tasks = task_store.list_tasks(kind=SOURCE_DISCOVERY_TASK_KIND)
            events = workflow_store.list_events(workflow_id=spec.workflow_id, limit=100)

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].input["workflow_id"], spec.workflow_id)
        self.assertEqual(tasks[0].input["missing_sources"], ["community_web"])
        self.assertIn("workflow_source_discovery_enqueued", [event["event_type"] for event in events])

    def test_source_discovery_retry_preserves_user_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_store = TaskStore(root / "agentic.sqlite3")
            enqueuer = SourceDiscoveryEnqueuer(task_store=task_store, state_dir=root)
            task = enqueuer.enqueue(
                workflow_id="wf_test",
                user_request="source_label: community_web\nsource_user_answer: 주식갤을 소스로 써.",
                missing_sources=["community_web"],
                feedback="검색 결과가 사용자 소스 힌트와 무관하다. 원래 힌트를 다시 보고 검색어를 고쳐라.",
            )

        self.assertEqual(task.input["workflow_id"], "wf_test")
        self.assertEqual(task.input["missing_sources"], ["community_web"])
        self.assertIn("사용자 소스 힌트", task.input["feedback"])


def _missing_source_workflow() -> WorkflowSpec:
    return WorkflowSpec(
        name="No preseed workflow",
        goal="Discover and monitor an unknown community source.",
        description="User asked for a recurring community trend workflow without providing a URL.",
        status=WorkflowStatus.PROPOSED,
        triggers=[{"type": "interval", "value": "interval:60s"}],
        sources=[{"type": "community_web", "mode": "requires_real_source_binding"}],
        outputs=[{"type": "report", "channel": "web"}],
        success_criteria=["A reviewable report is produced."],
        steps=[
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect",
                config={"source": "community_web"},
            ),
            WorkflowStep(step_id="analyze", step_type=StepType.ANALYZE, name="Analyze"),
            WorkflowStep(step_id="report", step_type=StepType.REPORT, name="Report"),
        ],
    )


if __name__ == "__main__":
    unittest.main()
