from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.scheduler import ScheduleStore
from agentic.sessions import SessionLogStore
from agentic.sources import SourceDefinition, SourceKind, SourceStore
from agentic.tooling import ToolingBacklogStore, ToolingKind, ToolingPlanner
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel import (
    CapabilityAdmission,
    CapabilityPlanner,
    IntentRouter,
    IntentType,
    PlanningSessionStore,
    StepType,
    WorkflowDesigner,
    WorkflowLifecycleService,
    WorkflowStore,
)


class Milestone11HarnessBackboneTests(unittest.TestCase):
    def test_browser_transaction_request_opens_planning_session(self) -> None:
        intent = IntentRouter().classify("MSI 2026 결승전 표 예매해줘")
        proposal = WorkflowDesigner().design("MSI 2026 결승전 표 예매해줘")

        self.assertEqual(intent.intent_type, IntentType.BROWSER_TRANSACTION)
        self.assertIsNone(proposal.spec)
        self.assertEqual(proposal.session.intent.intent_type, IntentType.BROWSER_TRANSACTION)
        self.assertEqual(proposal.session.missing_slots[0], "constraints")
        self.assertIn("수량", proposal.session.question or "")

    def test_planning_session_answer_creates_browser_transaction_spec(self) -> None:
        designer = WorkflowDesigner()
        proposal = designer.design("MSI 2026 결승전 표 예매해줘")

        continued = designer.continue_design(
            proposal.session,
            "2장, 1장당 20만원 이하, 결제 또는 예매확정 직전에는 반드시 물어봐.",
        )

        self.assertIsNotNone(continued.spec)
        assert continued.spec is not None
        self.assertEqual(continued.spec.intent_type, IntentType.BROWSER_TRANSACTION)
        step_types = {step.step_type for step in continued.spec.steps}
        self.assertIn(StepType.ASK_USER, step_types)
        self.assertIn(StepType.BROWSER_OBSERVE, step_types)
        self.assertIn(StepType.BROWSER_ACTION, step_types)
        self.assertIn(StepType.APPROVAL, step_types)
        self.assertEqual(continued.spec.policy["risk"], "high")

    def test_capability_gap_becomes_tooling_backlog(self) -> None:
        designer = WorkflowDesigner()
        proposal = designer.design("MSI 2026 결승전 표 예매해줘")
        continued = designer.continue_design(proposal.session, "1장, 가격 무관, 결제 전 승인.")
        assert continued.spec is not None

        capability_plan = CapabilityPlanner().plan(continued.spec)
        tooling_plan = ToolingPlanner().plan(capability_plan)

        admissions = {need.capability: need.admission for need in capability_plan.needs}
        self.assertEqual(admissions["connector:browser"], CapabilityAdmission.MISSING)
        self.assertTrue(any(request.capability == "connector:browser" for request in tooling_plan.requests))
        browser_request = next(
            request for request in tooling_plan.requests if request.capability == "connector:browser"
        )
        self.assertEqual(browser_request.kind, ToolingKind.CONNECTOR)
        self.assertEqual(browser_request.suggested_module, "agentic/browser/")
        self.assertEqual(browser_request.priority, 0)

    def test_planning_and_tooling_stores_are_durable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_store = PlanningSessionStore(root / "planning.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            proposal = WorkflowDesigner().design("MSI 2026 결승전 표 예매해줘")
            session_store.upsert(proposal.session)

            reloaded = PlanningSessionStore(root / "planning.sqlite3").get(proposal.session.session_id)
            continued = WorkflowDesigner().continue_design(reloaded, "2장, 중앙 좌석 선호, 결제 전 승인.")
            assert continued.spec is not None
            tooling_plan = ToolingPlanner().plan(CapabilityPlanner().plan(continued.spec))
            tooling_store.add_many(tooling_plan.requests)

            requests = ToolingBacklogStore(root / "tooling.sqlite3").list()

        self.assertEqual(reloaded.session_id, proposal.session.session_id)
        self.assertTrue(any(request.capability == "connector:browser" for request in requests))

    def test_web_design_answer_creates_workflow_and_tooling_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = TraceLogger(root / "trace.jsonl")
            planning_store = PlanningSessionStore(root / "planning.sqlite3")
            session_log_store = SessionLogStore(root / "sessions.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            app = create_app(
                channel_loop=None,
                approvals=ApprovalService(ApprovalStore(root / "approvals.jsonl"), trace),
                trace=trace,
                workflow_store=workflow_store,
                workflow_designer=WorkflowDesigner(),
                planning_session_store=planning_store,
                session_log_store=session_log_store,
                tooling_store=tooling_store,
            )

            response = _request(
                app,
                "POST",
                "/workflows/design",
                data={"message": "MSI 2026 결승전 표 예매해줘"},
            )
            sessions = _request(app, "GET", "/planning-sessions").json()
            session_id = sessions[0]["session_id"]
            answer_response = _request(
                app,
                "POST",
                f"/planning-sessions/{session_id}/answer",
                data={"answer": "2장, 20만원 이하, 결제와 예매확정 전 승인 필요."},
            )
            workflows = _request(app, "GET", "/workflows").json()
            tooling = _request(app, "GET", "/tooling").json()
            session_logs = _request(app, "GET", "/sessions").json()
            session_events = _request(app, "GET", f"/sessions/{session_logs[0]['session_id']}/events").json()

        self.assertEqual(response.status_code, 303)
        self.assertEqual(answer_response.status_code, 303)
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0]["intent_type"], IntentType.BROWSER_TRANSACTION.value)
        self.assertTrue(any(item["capability"] == "connector:browser" for item in tooling))
        self.assertEqual(len(session_logs), 1)
        self.assertEqual(workflows[0]["inputs"]["session_log_id"], session_logs[0]["session_id"])
        self.assertIn("user_request", [event["event_type"] for event in session_events])
        self.assertIn("interview_answer", [event["event_type"] for event in session_events])
        self.assertIn("workflow_proposed", [event["event_type"] for event in session_events])

    def test_web_planning_answer_auto_activates_bound_read_only_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "community.jsonl"
            source_file.write_text(
                '{"uri":"local://post/1","title":"AI trend","content_text":"ai chip demand trend"}\n',
                encoding="utf-8",
            )
            trace = TraceLogger(root / "trace.jsonl")
            planning_store = PlanningSessionStore(root / "planning.sqlite3")
            session_log_store = SessionLogStore(root / "sessions.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Enabled community source",
                    locator=source_file.as_uri(),
                    enabled=True,
                    metadata={"aliases": ["community_web"]},
                )
            )
            app = create_app(
                channel_loop=None,
                approvals=ApprovalService(ApprovalStore(root / "approvals.jsonl"), trace),
                trace=trace,
                workflow_store=workflow_store,
                source_store=source_store,
                workflow_designer=WorkflowDesigner(),
                planning_session_store=planning_store,
                session_log_store=session_log_store,
                tooling_store=tooling_store,
                workflow_lifecycle=WorkflowLifecycleService(
                    workflow_store=workflow_store,
                    source_store=source_store,
                    schedule_store=ScheduleStore(root / "schedules.sqlite3"),
                    artifact_store=artifact_store,
                    resource_store=resource_store,
                ),
            )

            _request(
                app,
                "POST",
                "/workflows/design",
                data={"message": "주식갤 자동 크롤링하고 주기적으로 트렌드 보고서 보내줘"},
            )
            session_id = _request(app, "GET", "/planning-sessions").json()[0]["session_id"]
            _request(
                app,
                "POST",
                f"/planning-sessions/{session_id}/answer",
                data={"answer": "1분마다 수집하고 1시간마다 분석해서 웹 보고서와 ntfy 알림으로 알려줘."},
            )
            workflows = _request(app, "GET", "/workflows").json()
            events = workflow_store.list_events(workflow_id=workflows[0]["workflow_id"])
            session_logs = _request(app, "GET", "/sessions").json()
            session_events = _request(app, "GET", f"/sessions/{session_logs[0]['session_id']}/events").json()

        self.assertEqual(workflows[0]["status"], "active")
        self.assertEqual(workflows[0]["inputs"]["source_binding_status"], "bound")
        self.assertEqual(workflows[0]["inputs"]["session_log_id"], session_logs[0]["session_id"])
        event_types = [event["event_type"] for event in events]
        self.assertIn("workflow_reviewed", event_types)
        self.assertIn("workflow_sources_bound", event_types)
        self.assertIn("workflow_activated", event_types)
        session_event_types = [event["event_type"] for event in session_events]
        self.assertIn("workflow_lifecycle_advanced", session_event_types)


def _request(app, method: str, path: str, data: dict[str, str] | None = None):
    body = urlencode(data or {}).encode("utf-8")
    headers = []
    if data is not None:
        headers.append((b"content-type", b"application/x-www-form-urlencoded"))

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    messages = []

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
    }
    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body_bytes = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return _Response(status, body_bytes)


class _Response:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body

    def json(self):
        import json

        return json.loads(self.body.decode("utf-8"))
