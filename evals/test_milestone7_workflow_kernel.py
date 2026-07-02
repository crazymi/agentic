from __future__ import annotations

import tempfile
import unittest
import asyncio
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.scheduler import ScheduleRecord, ScheduleStore, SchedulerRunner
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel import (
    CapabilityAdmission,
    CapabilityPlanner,
    IntentRouter,
    IntentType,
    StepType,
    WorkflowBuilder,
    WorkflowDesigner,
    WorkflowInterpreter,
    WorkflowLifecycleService,
    WorkflowStatus,
    WorkflowStore,
)
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep


class Milestone7WorkflowKernelTests(unittest.TestCase):
    def test_intent_router_classifies_core_request_shapes(self) -> None:
        router = IntentRouter()

        self.assertEqual(router.classify("1+1은 뭐지?").intent_type, IntentType.ANSWER_NOW)
        self.assertEqual(
            router.classify("매일 WSJ 읽고 보고서 줘").intent_type,
            IntentType.SCHEDULED_WORKFLOW,
        )
        self.assertEqual(
            router.classify("이 사이트 빈자리 뜨면 알려줘").intent_type,
            IntentType.WATCHER_WORKFLOW,
        )
        self.assertEqual(
            router.classify("이 repo 버그 수정하고 테스트해줘").intent_type,
            IntentType.CODING_WORKFLOW,
        )
        self.assertTrue(router.classify("").requires_clarification)

    def test_workflow_store_persists_lifecycle_and_blocks_unapproved_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = WorkflowStore(Path(tmpdir) / "workflows.sqlite3")
            spec = _local_spec("src_test")
            store.create_spec(spec)

            reloaded = WorkflowStore(Path(tmpdir) / "workflows.sqlite3").get_spec(spec.workflow_id)
            self.assertEqual(reloaded.workflow_id, spec.workflow_id)

            with self.assertRaises(ValueError):
                store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)

            store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            active = store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)

        self.assertEqual(active.status, WorkflowStatus.ACTIVE)

    def test_workflow_designer_asks_one_question_or_proposes_spec(self) -> None:
        designer = WorkflowDesigner()

        vague = designer.design("주기적으로 트렌드 알려줘")
        self.assertIsNone(vague.spec)
        self.assertEqual(vague.session.missing_slots[0], "source")
        self.assertIsNotNone(vague.session.question)

        proposal = designer.design("매일 WSJ 뉴스레터를 읽고 보고서로 알려줘")
        self.assertIsNotNone(proposal.spec)
        self.assertEqual(proposal.spec.status, WorkflowStatus.PROPOSED)
        self.assertEqual(proposal.spec.intent_type, IntentType.SCHEDULED_WORKFLOW)

    def test_workflow_designer_does_not_treat_meta_answer_as_cadence(self) -> None:
        designer = WorkflowDesigner()
        proposal = designer.design(
            "주식갤과 미국 주식 레딧을 계속 관찰해서 트렌드를 보고해주는 반복 자동화 워크플로우를 만들어줘"
        )

        first = designer.continue_design(
            proposal.session,
            "처음에는 유저와 인터뷰해서 소스, 주기, 저장 위치, 보고 기준을 확정하게 해.",
        )
        self.assertIn("cadence", first.session.missing_slots)

        second = designer.continue_design(
            first.session,
            "1분마다 수집하고 1시간마다 분석해서 웹 보고서와 ntfy 알림으로 알려줘.",
        )
        self.assertEqual(second.session.extracted_slots["cadence"], "interval:60s")
        self.assertEqual(second.session.status, "proposed")

    def test_capability_planner_flags_external_and_script_capabilities(self) -> None:
        planner = CapabilityPlanner()
        social = WorkflowDesigner().design(
            "30분마다 주식 커뮤니티 글을 모아서 트렌드 보고서로 알려줘"
        ).spec
        self.assertIsNotNone(social)
        plan = planner.plan(social)
        self.assertTrue(plan.requires_approval)
        self.assertIn(CapabilityAdmission.REQUIRES_APPROVAL, {need.admission for need in plan.needs})

        script_spec = WorkflowSpec(
            name="Script Probe",
            goal="Run reviewed script",
            steps=[
                WorkflowStep(
                    step_id="script",
                    step_type=StepType.RUN_SCRIPT,
                    name="Run generated script",
                    config={"artifact_id": "art_review_required"},
                )
            ],
        )
        script_plan = planner.plan(script_spec)
        self.assertEqual(script_plan.needs[0].admission, CapabilityAdmission.NEEDS_ARTIFACT_REVIEW)

    def test_interpreter_executes_approved_local_source_workflow_and_creates_report_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store, resource_store, source_runtime, spec = _local_source_spec(root)
            spec = workflow_store.create_spec(spec)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            builder = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=source_runtime,
                    resource_store=resource_store,
                )
            )

            result = builder.run_approved(spec)
            artifacts = artifact_store.list(run_id=result.run.run_id)

        self.assertTrue(result.ok)
        self.assertEqual(result.run.status.value, "completed")
        self.assertEqual(len(artifacts), 1)
        self.assertIn("Goal:", artifacts[0].content)

    def test_scheduler_runs_due_active_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            schedule_store = ScheduleStore(root / "schedules.sqlite3")
            source_store, resource_store, source_runtime, spec = _local_source_spec(root)
            spec = workflow_store.create_spec(spec)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.ACTIVE)
            schedule_store.create(ScheduleRecord(workflow_id=spec.workflow_id, trigger={"type": "manual"}))
            runner = SchedulerRunner(
                schedule_store=schedule_store,
                workflow_store=workflow_store,
                builder=WorkflowBuilder(
                    WorkflowInterpreter(
                        workflow_store=workflow_store,
                        artifact_store=artifact_store,
                        source_runtime=source_runtime,
                        resource_store=resource_store,
                    )
                ),
            )

            results = runner.run_due_once()

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)

    def test_web_ui_design_review_and_run_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = TraceLogger(root / "trace.jsonl")
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store, resource_store, source_runtime, _ = _local_source_spec(root)
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Mail source",
                    locator=(root / "source.jsonl").as_uri(),
                    enabled=True,
                    metadata={"aliases": ["mail"]},
                )
            )
            app = create_app(
                channel_loop=None,
                approvals=ApprovalService(ApprovalStore(root / "approvals.jsonl"), trace),
                trace=trace,
                workflow_store=workflow_store,
                source_store=source_store,
                workflow_designer=WorkflowDesigner(),
                workflow_builder=WorkflowBuilder(
                    WorkflowInterpreter(
                        workflow_store=workflow_store,
                        artifact_store=artifact_store,
                        source_runtime=source_runtime,
                        resource_store=resource_store,
                    )
                ),
                workflow_lifecycle=WorkflowLifecycleService(
                    workflow_store=workflow_store,
                    source_store=source_store,
                    schedule_store=ScheduleStore(root / "schedules.sqlite3"),
                    artifact_store=artifact_store,
                    resource_store=resource_store,
                ),
            )
            response = _request(
                app,
                "POST",
                "/workflows/design",
                data={"message": "매일 WSJ 뉴스레터를 읽고 보고서를 생성해줘"},
            )
            workflows = _request(app, "GET", "/workflows").json()
            workflow_id = workflows[0]["workflow_id"]
            _request(app, "POST", f"/workflows/{workflow_id}/run")
            runs = _request(app, "GET", "/workflow-runs").json()

        self.assertEqual(response.status_code, 303)
        self.assertEqual(workflows[0]["status"], "active")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "completed")

    def test_vertical_probes_are_representable_as_workflow_specs(self) -> None:
        requests = [
            "매일 WSJ 뉴스레터를 읽고 보고서로 알려줘",
            "30분마다 주식 커뮤니티 글을 모아서 트렌드 보고서로 알려줘",
            "내 아이디어 메모를 받아서 연결하고 보고서로 정리해줘",
            "이 사이트 빈자리 뜨면 알려줘",
            "이 repo 버그 수정하고 테스트해줘",
        ]
        specs = [WorkflowDesigner().design(request).spec for request in requests]

        self.assertEqual(len([spec for spec in specs if spec is not None]), len(requests))
        for spec in specs:
            self.assertGreaterEqual(len(spec.steps), 3)


def _local_source_spec(root: Path) -> tuple[SourceStore, ResourceStore, SourceRuntime, WorkflowSpec]:
    source_file = root / "source.jsonl"
    source_file.write_text(
        '{"uri":"local://item-1","title":"Workflow source","content_text":"Workflow kernel collects real local data."}\n',
        encoding="utf-8",
    )
    source_store = SourceStore(root / "sources.sqlite3")
    resource_store = ResourceStore(root / "resources.sqlite3")
    source = source_store.add_source(
        SourceDefinition(
            kind=SourceKind.LOCAL_FILE,
            name="Local workflow source",
            locator=source_file.as_uri(),
            enabled=True,
        )
    )
    source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
    return source_store, resource_store, source_runtime, _local_spec(source.source_id)


def _local_spec(source_id: str) -> WorkflowSpec:
    return WorkflowSpec(
        name="Local Source Workflow",
        goal="Prove workflow kernel execution",
        intent_type=IntentType.SCHEDULED_WORKFLOW,
        triggers=[{"type": "manual"}],
        sources=[{"type": "local_file", "source_id": source_id}],
        steps=[
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect local items",
                config={"source": "local_file", "source_id": source_id},
            ),
            WorkflowStep(
                step_id="analyze",
                step_type=StepType.ANALYZE,
                name="Analyze local items",
                depends_on=["collect"],
            ),
            WorkflowStep(
                step_id="report",
                step_type=StepType.REPORT,
                name="Report local results",
                depends_on=["analyze"],
            ),
        ],
    )


class AsgiResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.text = body.decode("utf-8")

    def json(self):
        import json

        return json.loads(self.text)


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
