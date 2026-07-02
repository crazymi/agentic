from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.sources.discovery import (
    SOURCE_DISCOVERY_TASK_KIND,
    SourceCandidateStore,
    SourceDiscoveryEnqueuer,
    append_source_discovery_session_event,
    build_source_candidate_service,
    _candidate_instruction,
    _search_instruction,
)
from agentic.sessions import SessionLogStore
from agentic.app.cli import _declared_source_labels, _workflow_source_context
from agentic.sources import SourceDefinition, SourceKind
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

    def test_source_candidate_rejects_placeholder_locator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = build_source_candidate_service(Path(tmpdir))
            with self.assertRaises(ValueError):
                service.propose(
                    workflow_id="wf_test",
                    requested_source="community_web",
                    kind="web_page",
                    name="Placeholder",
                    locator="https://result-url",
                    confidence=0.8,
                    auto_register=True,
                )

    def test_lifecycle_missing_source_enqueues_source_discovery_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_store = SessionLogStore(root / "sessions.sqlite3")
            session = session_store.start_session("workflow_design")
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            task_store = TaskStore(root / "agentic.sqlite3")
            spec = workflow_store.create_spec(
                _missing_source_workflow(inputs={"session_log_id": session.session_id})
            )
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
        self.assertEqual(tasks[0].input["session_log_id"], session.session_id)
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
                session_log_id="sess_test",
            )

        self.assertEqual(task.input["workflow_id"], "wf_test")
        self.assertEqual(task.input["missing_sources"], ["community_web"])
        self.assertIn("사용자 소스 힌트", task.input["feedback"])
        self.assertEqual(task.input["session_log_id"], "sess_test")

    def test_source_discovery_feedback_can_be_logged_as_user_session_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_store = SessionLogStore(root / "sessions.sqlite3")
            session = session_store.start_session("workflow_design")
            append_source_discovery_session_event(
                root,
                session.session_id,
                "source_discovery_feedback",
                role="user",
                content="노이즈가 너무 많다. 네 도구로 원인을 진단하고 전략을 수정해봐.",
                payload={"workflow_id": "wf_test", "missing_sources": ["community_web"]},
            )
            events = session_store.list_events(session.session_id)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "source_discovery_feedback")
        self.assertEqual(events[0].role, "user")
        self.assertIn("노이즈가 너무 많다", events[0].content)

    def test_lifecycle_advance_is_idempotent_for_active_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.WEB_PAGE,
                    name="Community source",
                    locator="https://example.com/community",
                    enabled=True,
                    metadata={"aliases": ["community_web"]},
                )
            )
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            spec = workflow_store.create_spec(
                _missing_source_workflow(
                    inputs={
                        "source_ids": [source.source_id],
                        "source_binding_status": "bound",
                    }
                )
            )
            approved = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            workflow_store.transition_spec(approved.workflow_id, WorkflowStatus.ACTIVE)
            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=source_store,
            )
            result = service.advance_after_proposal(spec.workflow_id)
            updated = workflow_store.get_spec(spec.workflow_id)

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "active")
        self.assertEqual(updated.sources[0]["requested"], "community_web")

    def test_retry_source_labels_prefer_original_requested_label_after_binding(self) -> None:
        labels = _declared_source_labels(
            {
                "sources": [
                    {
                        "requested": "community_web",
                        "kind": "web_page",
                        "name": "Agent discovered source",
                    }
                ]
            }
        )

        self.assertEqual(labels, ["community_web"])

    def test_workflow_source_context_redacts_bound_source_locator(self) -> None:
        context = _workflow_source_context(
            {
                "description": "Monitor a source.",
                "goal": "Find trends.",
                "inputs": {
                    "slot_answers": {
                        "source": "주식갤을 소스로 써.",
                        "cadence": "1분마다.",
                    }
                },
                "sources": [
                    {
                        "requested": "community_web",
                        "kind": "web_page",
                        "locator": "https://example.com/hidden",
                        "source_id": "src_hidden",
                    }
                ],
            }
        )

        self.assertIn("community_web", context)
        self.assertIn("주식갤", context)
        self.assertNotIn("https://example.com/hidden", context)
        self.assertNotIn("src_hidden", context)

    def test_feedback_source_discovery_instruction_asks_for_alternative_without_locator(self) -> None:
        search = _search_instruction(
            workflow_id="wf_test",
            user_request="source: community_web",
            missing_sources=["community_web"],
            feedback="previous source was noisy",
            existing_source_names=["Noisy Source"],
        )
        candidate = _candidate_instruction(
            workflow_id="wf_test",
            user_request="source: community_web",
            missing_sources=["community_web"],
            search_report="[]",
            feedback_present=True,
            existing_source_names=["Noisy Source"],
        )

        self.assertIn("better or more precise alternative", search)
        self.assertIn("Already tried source names: Noisy Source", search)
        self.assertIn("Prefer a clearly better alternative", candidate)
        self.assertNotIn("https://", search)


def _missing_source_workflow(inputs: dict | None = None) -> WorkflowSpec:
    return WorkflowSpec(
        name="No preseed workflow",
        goal="Discover and monitor an unknown community source.",
        description="User asked for a recurring community trend workflow without providing a URL.",
        status=WorkflowStatus.PROPOSED,
        inputs=inputs or {},
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
