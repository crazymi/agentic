from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.scheduler import ScheduleStore, SchedulerRunner
from agentic.sessions import SessionLogStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.workflow_kernel import (
    CapabilityAdmission,
    CapabilityPlanner,
    StepType,
    WorkflowBuilder,
    WorkflowInterpreter,
    WorkflowSpec,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStore,
)
from agentic.workflow_kernel.lifecycle import WorkflowLifecycleService


class SessionLogTests(unittest.TestCase):
    def test_session_log_persists_full_turn_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionLogStore(Path(tmp) / "sessions.sqlite3")
            session = store.start_session("workflow interview", metadata={"request": "do work"})
            store.append_event(session.session_id, "user_request", role="user", content="do work")
            store.append_event(session.session_id, "interview_question", role="agent", content="source?")
            store.append_event(session.session_id, "interview_answer", role="user", content="reddit")

            reloaded = SessionLogStore(Path(tmp) / "sessions.sqlite3")
            events = reloaded.list_events(session.session_id)

        self.assertEqual([event.event_type for event in events], ["user_request", "interview_question", "interview_answer"])
        self.assertEqual(events[2].content, "reddit")


class WorkflowLifecycleTests(unittest.TestCase):
    def test_bound_web_page_read_is_allowed_without_extra_approval(self) -> None:
        spec = _spec_with_sources(["reddit"])
        record = spec.to_record()
        record["sources"] = [
            {
                "requested": "reddit",
                "source_id": "src_live",
                "kind": "web_page",
                "name": "Live page",
                "locator": "https://example.com",
                "mode": "enabled_source_binding",
            }
        ]
        record["inputs"] = {"source_binding_status": "bound", "source_ids": ["src_live"]}
        record["policy"] = {"lifecycle": {"source_binding_status": "bound"}}
        record["steps"][0]["config"] = {
            "source": "web_page",
            "source_id": "src_live",
            "source_ids": ["src_live"],
        }
        plan = CapabilityPlanner().plan(WorkflowSpec.from_record(record))

        self.assertFalse(plan.requires_approval)
        self.assertIn(CapabilityAdmission.ALLOWED, {need.admission for need in plan.needs})

    def test_low_risk_bound_ntfy_report_is_allowed_without_extra_approval(self) -> None:
        spec = _spec_with_sources(["reddit"])
        record = spec.to_record()
        record["sources"] = [
            {
                "requested": "reddit",
                "source_id": "src_live",
                "kind": "web_page",
                "name": "Live page",
                "locator": "https://example.com",
                "mode": "enabled_source_binding",
            }
        ]
        record["inputs"] = {"source_binding_status": "bound", "source_ids": ["src_live"]}
        record["policy"] = {"risk": "low", "activation_requires_approval": False}
        record["outputs"] = [{"type": "report", "channel": "ntfy"}]
        record["steps"][0]["config"] = {
            "source": "web_page",
            "source_id": "src_live",
            "source_ids": ["src_live"],
        }
        record["steps"].append(
            {
                "step_id": "notify",
                "step_type": "notify",
                "name": "Notify",
                "config": {"channel": "ntfy"},
                "depends_on": ["report"],
            }
        )
        plan = CapabilityPlanner().plan(WorkflowSpec.from_record(record))

        self.assertFalse(plan.requires_approval)
        admissions = {need.capability: need.admission for need in plan.needs}
        self.assertEqual(admissions["channel:ntfy"], CapabilityAdmission.ALLOWED)

    def test_review_records_source_binding_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow_store = WorkflowStore(Path(tmp) / "workflows.sqlite3")
            source_store = SourceStore(Path(tmp) / "sources.sqlite3")
            spec = workflow_store.create_spec(_spec_with_source("reddit"))

            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=source_store,
            )
            review = service.review(spec.workflow_id)
            binding = service.bind_sources(spec.workflow_id)

            self.assertTrue(review.ok)
            self.assertIn("source_binding_missing", review.warnings)
            self.assertFalse(binding.ok)
            self.assertEqual(binding.missing_sources, ["reddit"])

    def test_source_binding_gates_approval_and_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow_store = WorkflowStore(Path(tmp) / "workflows.sqlite3")
            source_store = SourceStore(Path(tmp) / "sources.sqlite3")
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.FEED,
                    name="Market community feed",
                    locator=(Path(tmp) / "feed.jsonl").as_uri(),
                    enabled=True,
                    metadata={"aliases": ["reddit"]},
                )
            )
            spec = workflow_store.create_spec(_spec_with_source("reddit"))
            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=source_store,
            )

            binding = service.bind_sources(spec.workflow_id)
            approved = service.approve(spec.workflow_id)
            active = service.activate(spec.workflow_id)

            self.assertTrue(binding.ok)
            self.assertEqual(approved.status, WorkflowStatus.APPROVED)
            self.assertEqual(active.status, WorkflowStatus.ACTIVE)
            rebound = workflow_store.get_spec(spec.workflow_id)
            self.assertEqual(rebound.inputs["source_binding_status"], "bound")
            self.assertTrue(rebound.steps[0].config["source_id"].startswith("src_"))

    def test_approval_fails_without_source_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow_store = WorkflowStore(Path(tmp) / "workflows.sqlite3")
            source_store = SourceStore(Path(tmp) / "sources.sqlite3")
            spec = workflow_store.create_spec(_spec_with_source("dcinside-gallery"))
            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=source_store,
            )

            with self.assertRaises(ValueError):
                service.approve(spec.workflow_id)

            events = workflow_store.list_events(workflow_id=spec.workflow_id)
            self.assertIn("workflow_approval_blocked", [event["event_type"] for event in events])

    def test_multi_source_binding_activation_and_due_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reddit_file = root / "reddit.jsonl"
            dcinside_file = root / "dcinside.jsonl"
            reddit_file.write_text(
                '{"uri":"local://reddit/1","title":"AI chip rally","text":"ai chips earnings trend"}\n',
                encoding="utf-8",
            )
            dcinside_file.write_text(
                '{"uri":"local://dc/1","title":"반도체 관심","text":"반도체 수급 관심 증가"}\n',
                encoding="utf-8",
            )
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            schedule_store = ScheduleStore(root / "schedules.sqlite3")
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Enabled Reddit source",
                    locator=reddit_file.as_uri(),
                    enabled=True,
                    metadata={"aliases": ["reddit"]},
                )
            )
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Enabled DCInside source",
                    locator=dcinside_file.as_uri(),
                    enabled=True,
                    metadata={"aliases": ["dcinside-gallery"]},
                )
            )
            spec = workflow_store.create_spec(_spec_with_sources(["reddit", "dcinside-gallery"]))
            service = WorkflowLifecycleService(
                workflow_store=workflow_store,
                source_store=source_store,
                schedule_store=schedule_store,
                artifact_store=artifact_store,
                resource_store=resource_store,
            )

            binding = service.bind_sources(spec.workflow_id)
            approved = service.approve(spec.workflow_id)
            active = service.activate(spec.workflow_id)
            schedules = schedule_store.list_due()
            runner = SchedulerRunner(
                schedule_store=schedule_store,
                workflow_store=workflow_store,
                builder=WorkflowBuilder(
                    WorkflowInterpreter(
                        workflow_store=workflow_store,
                        artifact_store=artifact_store,
                        source_runtime=SourceRuntime(
                            source_store=source_store,
                            resource_store=resource_store,
                        ),
                        resource_store=resource_store,
                    )
                ),
            )
            results = runner.run_due_once()
            run = workflow_store.get_run(results[0].workflow_run_id)
            schedule_after_run = schedule_store.get(schedules[0].schedule_id)

        self.assertTrue(binding.ok)
        self.assertEqual(approved.status, WorkflowStatus.APPROVED)
        self.assertEqual(active.status, WorkflowStatus.ACTIVE)
        self.assertEqual(len(schedules), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(run.step_results["collect"]["collected_count"], 2)
        self.assertEqual(len(run.artifacts), 1)
        self.assertIsNotNone(schedule_after_run.next_run_at)


def _spec_with_source(source: str) -> WorkflowSpec:
    return _spec_with_sources([source])


def _spec_with_sources(sources: list[str]) -> WorkflowSpec:
    return WorkflowSpec(
        name="community trend monitor",
        goal="watch community trend signals",
        status=WorkflowStatus.PROPOSED,
        triggers=[{"type": "interval", "value": "interval:60s"}],
        sources=[{"kind": source} for source in sources],
        outputs=[{"kind": "report"}],
        success_criteria=["A report is produced from real bound sources."],
        steps=[
            WorkflowStep(step_id="collect", step_type=StepType.COLLECT, name="Collect"),
            WorkflowStep(step_id="analyze", step_type=StepType.ANALYZE, name="Analyze"),
            WorkflowStep(step_id="report", step_type=StepType.REPORT, name="Report"),
        ],
    )


if __name__ == "__main__":
    unittest.main()
