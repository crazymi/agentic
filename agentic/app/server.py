from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agentic.app.web_templates import render_home
from agentic.artifacts import ArtifactStore
from agentic.approvals.service import ApprovalService
from agentic.ops import HealthMonitor
from agentic.delivery import DeliveryStore
from agentic.probes import (
    DEFAULT_PROBE_ANSWERS,
    DEFAULT_PROBE_REQUEST,
    WORKFLOW_BUILDER_PROBE_TASK_KIND,
)
from agentic.resources.store import ResourceStore
from agentic.scheduler import ScheduleStore
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.daemon_loop import RuntimeDaemonLoop
from agentic.runtime.durable_channel_loop import DurableChannelLoop
from agentic.runtime.events import InboundMessage
from agentic.runtime.task_control import TaskControl
from agentic.sessions import SessionLogStore, SessionRecord
from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.sources.discovery import SourceDiscoveryEnqueuer
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger
from agentic.tooling import ToolingBacklogStore, ToolingPlanner
from agentic.workflow_kernel import (
    CapabilityPlanner,
    PlanningSessionStore,
    WorkflowBuilder,
    WorkflowDesigner,
    WorkflowInterpreter,
    WorkflowLifecycleService,
    WorkflowSpec,
    WorkflowStatus,
    WorkflowStore,
)


class WebState:
    def __init__(
        self,
        *,
        channel_loop: ChannelLoop | None,
        durable_channel_loop: DurableChannelLoop | None,
        approvals: ApprovalService,
        trace: TraceLogger,
        task_store: TaskStore | None,
        task_control: TaskControl | None,
        workflow_store: WorkflowStore | None,
        source_store: SourceStore | None,
        workflow_builder: WorkflowBuilder | None,
        workflow_designer: WorkflowDesigner | None,
        workflow_lifecycle: WorkflowLifecycleService | None,
        planning_session_store: PlanningSessionStore | None,
        session_log_store: SessionLogStore | None,
        tooling_store: ToolingBacklogStore | None,
        skill_workshop: SkillWorkshopService | None,
        health_monitor: HealthMonitor | None,
        health_export_path: Path | None,
        delivery_store: DeliveryStore | None,
        runtime_daemon: RuntimeDaemonLoop | None,
    ):
        self.channel_loop = channel_loop
        self.durable_channel_loop = durable_channel_loop
        self.approvals = approvals
        self.trace = trace
        self.task_store = task_store
        self.task_control = task_control
        self.workflow_store = workflow_store
        self.source_store = source_store
        self.workflow_builder = workflow_builder
        self.workflow_designer = workflow_designer
        self.workflow_lifecycle = workflow_lifecycle
        self.planning_session_store = planning_session_store
        self.session_log_store = session_log_store
        self.tooling_store = tooling_store
        self.skill_workshop = skill_workshop
        self.health_monitor = health_monitor
        self.health_export_path = health_export_path
        self.delivery_store = delivery_store
        self.runtime_daemon = runtime_daemon
        self.messages: list[dict[str, Any]] = []


def create_app(
    *,
    channel_loop: ChannelLoop | None,
    approvals: ApprovalService,
    trace: TraceLogger,
    durable_channel_loop: DurableChannelLoop | None = None,
    task_store: TaskStore | None = None,
    task_control: TaskControl | None = None,
    workflow_store: WorkflowStore | None = None,
    source_store: SourceStore | None = None,
    workflow_builder: WorkflowBuilder | None = None,
    workflow_designer: WorkflowDesigner | None = None,
    workflow_lifecycle: WorkflowLifecycleService | None = None,
    planning_session_store: PlanningSessionStore | None = None,
    session_log_store: SessionLogStore | None = None,
    tooling_store: ToolingBacklogStore | None = None,
    skill_workshop: SkillWorkshopService | None = None,
    health_monitor: HealthMonitor | None = None,
    health_export_path: str | Path | None = None,
    delivery_store: DeliveryStore | None = None,
    runtime_daemon: RuntimeDaemonLoop | None = None,
) -> FastAPI:
    app = FastAPI(title="agentic")
    state = WebState(
        channel_loop=channel_loop,
        durable_channel_loop=durable_channel_loop,
        approvals=approvals,
        trace=trace,
        task_store=task_store,
        task_control=task_control,
        workflow_store=workflow_store,
        source_store=source_store,
        workflow_builder=workflow_builder,
        workflow_designer=workflow_designer,
        workflow_lifecycle=workflow_lifecycle,
        planning_session_store=planning_session_store,
        session_log_store=session_log_store,
        tooling_store=tooling_store,
        skill_workshop=skill_workshop,
        health_monitor=health_monitor,
        health_export_path=Path(health_export_path) if health_export_path is not None else None,
        delivery_store=delivery_store,
        runtime_daemon=runtime_daemon,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ops/health")
    async def ops_health() -> dict[str, Any]:
        if state.health_monitor is None:
            return {"status": "degraded", "reason": "health monitor is not configured"}
        return state.health_monitor.snapshot().to_record()

    @app.post("/ops/health/export")
    async def export_ops_health() -> RedirectResponse:
        if state.health_monitor is not None and state.health_export_path is not None:
            state.health_monitor.export_snapshot(state.health_export_path)
        return RedirectResponse("/", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    async def home() -> str:
        return render_home(
            messages=state.messages,
            approvals=[item.to_record() for item in state.approvals.get_pending()],
            tasks=_task_records(state.task_store),
            workflows=_workflow_records(state.workflow_store),
            workflow_runs=_workflow_run_records(state.workflow_store),
            planning_sessions=_planning_session_records(state.planning_session_store),
            session_logs=_session_records(state.session_log_store),
            tooling_requests=_tooling_records(state.tooling_store),
            skill_proposals=_skill_proposal_records(state.skill_workshop),
            deliveries=_delivery_records(state.delivery_store),
            daemon=_daemon_record(state.runtime_daemon),
            health=state.health_monitor.snapshot().to_record() if state.health_monitor is not None else None,
            traces=[
                {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "timestamp": event.timestamp,
                }
                for event in state.trace.read_events()
            ],
        )

    @app.post("/messages")
    async def post_message(request: Request) -> RedirectResponse:
        body = (await request.body()).decode("utf-8")
        message = parse_qs(body).get("message", [""])[0]
        inbound = InboundMessage(text=message, channel="web")
        state.messages.append({"role": "user", "text": message})
        if state.durable_channel_loop is not None:
            response = state.durable_channel_loop.handle_message(inbound)
            response_text = response.text
        elif state.channel_loop is None:
            response_text = "Channel loop is not configured."
        else:
            response = state.channel_loop.handle_message(inbound)
            response_text = response.text
        state.messages.append({"role": "agent", "text": response_text})
        return RedirectResponse("/", status_code=303)

    @app.get("/approvals")
    async def list_approvals() -> list[dict[str, Any]]:
        return [item.to_record() for item in state.approvals.get_pending()]

    @app.get("/tasks")
    async def list_tasks() -> list[dict[str, Any]]:
        return _task_records(state.task_store)

    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str) -> dict[str, Any]:
        if state.task_store is None:
            return {"error": "task store is not configured"}
        return _task_record(state.task_store.get_task(task_id))

    @app.get("/workflows")
    async def list_workflows() -> list[dict[str, Any]]:
        return _workflow_records(state.workflow_store)

    @app.get("/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str) -> dict[str, Any]:
        if state.workflow_store is None:
            return {"error": "workflow store is not configured"}
        return state.workflow_store.get_spec(workflow_id).to_record()

    @app.get("/workflow-runs")
    async def list_workflow_runs() -> list[dict[str, Any]]:
        return _workflow_run_records(state.workflow_store)

    @app.get("/planning-sessions")
    async def list_planning_sessions() -> list[dict[str, Any]]:
        return _planning_session_records(state.planning_session_store)

    @app.get("/sessions")
    async def list_sessions() -> list[dict[str, Any]]:
        return _session_records(state.session_log_store)

    @app.get("/sessions/{session_id}/events")
    async def list_session_events(session_id: str) -> list[dict[str, Any]]:
        if state.session_log_store is None:
            return []
        return [event.to_record() for event in state.session_log_store.list_events(session_id)]

    @app.get("/tooling")
    async def list_tooling() -> list[dict[str, Any]]:
        return _tooling_records(state.tooling_store)

    @app.get("/sources")
    async def list_sources() -> list[dict[str, Any]]:
        if state.source_store is None:
            return []
        return [source.to_record() for source in state.source_store.list_sources(limit=50)]

    @app.post("/sources/web")
    async def add_web_source(request: Request) -> RedirectResponse:
        if state.source_store is None:
            state.messages.append({"role": "agent", "text": "Source store is not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        parsed = parse_qs(body)
        url = parsed.get("url", [""])[0].strip()
        name = parsed.get("name", ["Web source"])[0].strip() or "Web source"
        aliases = [
            item.strip()
            for raw in parsed.get("aliases", [""])[0].split(",")
            for item in [raw]
            if item.strip()
        ]
        if not url:
            state.messages.append({"role": "agent", "text": "Source URL is required."})
            return RedirectResponse("/", status_code=303)
        source = state.source_store.add_source(
            SourceDefinition(
                kind=SourceKind.WEB_PAGE,
                name=name,
                locator=url,
                enabled=True,
                metadata={"aliases": aliases, "registered_from": "web"},
            )
        )
        state.messages.append({"role": "agent", "text": f"Source registered: {source.source_id}"})
        return RedirectResponse("/", status_code=303)

    @app.get("/deliveries")
    async def list_deliveries() -> list[dict[str, Any]]:
        return _delivery_records(state.delivery_store)

    @app.get("/daemon")
    async def daemon_status() -> dict[str, Any]:
        if state.runtime_daemon is None:
            return {"running": False, "reason": "runtime daemon is not configured"}
        return _daemon_record(state.runtime_daemon) or {"running": False}

    @app.post("/daemon/tick")
    async def daemon_tick() -> RedirectResponse:
        if state.runtime_daemon is not None:
            result = state.runtime_daemon.run_once()
            state.messages.append({"role": "agent", "text": f"Runtime tick completed: {result.to_record()}"})
        return RedirectResponse("/", status_code=303)

    @app.get("/skills/proposals")
    async def list_skill_proposals() -> list[dict[str, Any]]:
        return _skill_proposal_records(state.skill_workshop)

    @app.post("/workflows/design")
    async def design_workflow(request: Request) -> RedirectResponse:
        if state.workflow_designer is None or state.workflow_store is None:
            state.messages.append({"role": "agent", "text": "Workflow designer is not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        message = parse_qs(body).get("message", [""])[0]
        proposal = state.workflow_designer.design(message)
        session_log = _start_design_session_log(state, message, proposal.session)
        if state.planning_session_store is not None:
            state.planning_session_store.upsert(proposal.session)
        if proposal.session.question:
            _append_session_event(
                state,
                session_log,
                "interview_question",
                role="agent",
                content=proposal.session.question,
                payload={"missing_slots": proposal.session.missing_slots},
            )
        if proposal.spec is not None:
            spec = _attach_session_log(
                proposal.spec,
                session_log_id=session_log.session_id if session_log is not None else "",
                planning_session_id=proposal.session.session_id,
            )
            state.workflow_store.create_spec(spec)
            _append_session_event(
                state,
                session_log,
                "workflow_proposed",
                role="agent",
                content=spec.name,
                payload={"workflow": spec.to_record()},
            )
            _record_tooling_backlog(spec, state.tooling_store)
            advance = _advance_workflow_lifecycle(state, spec.workflow_id)
            _append_session_event(
                state,
                session_log,
                "workflow_lifecycle_advanced",
                role="runtime",
                content=str((advance or {}).get("status") or ""),
                payload=advance or {},
            )
        state.messages.append({"role": "user", "text": message})
        agent_text = proposal.to_markdown()
        _append_session_event(state, session_log, "agent_response", role="agent", content=agent_text)
        state.messages.append({"role": "agent", "text": agent_text})
        return RedirectResponse("/", status_code=303)

    @app.post("/probes/workflow-builder")
    async def run_workflow_builder_probe_task(request: Request) -> RedirectResponse:
        if state.durable_channel_loop is None:
            state.messages.append({"role": "agent", "text": "Durable runtime is not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        parsed = parse_qs(body)
        request_text = parsed.get("request", [DEFAULT_PROBE_REQUEST])[0] or DEFAULT_PROBE_REQUEST
        raw_answers = parsed.get("answers", [""])[0]
        answers = [
            line.strip()
            for line in raw_answers.splitlines()
            if line.strip()
        ] or list(DEFAULT_PROBE_ANSWERS)
        task = state.durable_channel_loop.store.create_task(
            kind=WORKFLOW_BUILDER_PROBE_TASK_KIND,
            input={"request": request_text, "answers": answers},
        )
        state.trace.record(
            "task_enqueued",
            {"task_id": task.task_id, "kind": task.kind, "source": "web_probe"},
        )
        state.durable_channel_loop.pool.kick()
        state.messages.append({"role": "user", "text": request_text})
        state.messages.append(
            {
                "role": "agent",
                "text": f"Workflow-builder probe task queued: {task.task_id}",
            }
        )
        return RedirectResponse("/", status_code=303)

    @app.post("/skills/proposals/{proposal_id}/request-apply")
    async def request_skill_proposal_apply(proposal_id: str) -> RedirectResponse:
        if state.skill_workshop is None:
            state.messages.append({"role": "agent", "text": "Skill workshop is not configured."})
            return RedirectResponse("/", status_code=303)
        try:
            approval = state.skill_workshop.request_apply(
                proposal_id,
                approvals=state.approvals,
            )
            state.messages.append(
                {
                    "role": "agent",
                    "text": f"Skill apply approval requested: {approval.approval_id}",
                }
            )
        except Exception as exc:
            state.messages.append({"role": "agent", "text": f"Skill apply request failed: {exc}"})
        return RedirectResponse("/", status_code=303)

    @app.post("/skills/proposals/{proposal_id}/apply")
    async def apply_skill_proposal(proposal_id: str, request: Request) -> RedirectResponse:
        if state.skill_workshop is None:
            state.messages.append({"role": "agent", "text": "Skill workshop is not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        approval_id = parse_qs(body).get("approval_id", [""])[0]
        try:
            approval = state.approvals.get(approval_id)
            proposal = state.skill_workshop.apply(proposal_id, approval=approval)
            state.messages.append(
                {
                    "role": "agent",
                    "text": f"Skill proposal applied: {proposal.target_skill_name}",
                }
            )
        except Exception as exc:
            state.messages.append({"role": "agent", "text": f"Skill apply failed: {exc}"})
        return RedirectResponse("/", status_code=303)

    @app.post("/planning-sessions/{session_id}/answer")
    async def answer_planning_session(session_id: str, request: Request) -> RedirectResponse:
        if (
            state.workflow_designer is None
            or state.workflow_store is None
            or state.planning_session_store is None
        ):
            state.messages.append({"role": "agent", "text": "Planning sessions are not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        answer = parse_qs(body).get("answer", [""])[0]
        session = state.planning_session_store.get(session_id)
        session_log = _find_session_log_by_planning_session(state, session_id)
        if session_log is None:
            session_log = _start_design_session_log(state, session.user_request, session)
        _append_session_event(
            state,
            session_log,
            "interview_answer",
            role="user",
            content=answer,
            payload={"planning_session_id": session_id, "missing_slots": session.missing_slots},
        )
        proposal = state.workflow_designer.continue_design(session, answer)
        state.planning_session_store.upsert(proposal.session)
        if proposal.session.question:
            _append_session_event(
                state,
                session_log,
                "interview_question",
                role="agent",
                content=proposal.session.question,
                payload={"missing_slots": proposal.session.missing_slots},
            )
        if proposal.spec is not None:
            spec = _attach_session_log(
                proposal.spec,
                session_log_id=session_log.session_id if session_log is not None else "",
                planning_session_id=session_id,
            )
            state.workflow_store.create_spec(spec)
            _append_session_event(
                state,
                session_log,
                "workflow_proposed",
                role="agent",
                content=spec.name,
                payload={"workflow": spec.to_record()},
            )
            _record_tooling_backlog(spec, state.tooling_store)
            advance = _advance_workflow_lifecycle(state, spec.workflow_id)
            if advance is not None:
                _append_session_event(
                    state,
                    session_log,
                    "workflow_lifecycle_advanced",
                    role="runtime",
                    content=str(advance.get("status") or ""),
                    payload=advance,
                )
                state.messages.append(
                    {
                        "role": "agent",
                        "text": f"Workflow lifecycle advanced: {advance.get('status')}",
                    }
                )
        state.messages.append({"role": "user", "text": answer})
        agent_text = proposal.to_markdown()
        _append_session_event(state, session_log, "agent_response", role="agent", content=agent_text)
        state.messages.append({"role": "agent", "text": agent_text})
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/approve")
    async def approve_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_lifecycle is not None:
            try:
                state.workflow_lifecycle.approve(workflow_id)
            except Exception as exc:
                state.messages.append({"role": "agent", "text": f"Workflow approval failed: {exc}"})
        elif state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.APPROVED)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/activate")
    async def activate_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_lifecycle is not None:
            try:
                state.workflow_lifecycle.activate(workflow_id)
            except Exception as exc:
                state.messages.append({"role": "agent", "text": f"Workflow activation failed: {exc}"})
        elif state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.ACTIVE)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/pause")
    async def pause_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.PAUSED)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/run")
    async def run_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_lifecycle is not None:
            try:
                state.workflow_lifecycle.run_once(workflow_id)
            except Exception as exc:
                state.messages.append({"role": "agent", "text": f"Workflow run failed: {exc}"})
        elif state.workflow_store is not None and state.workflow_builder is not None:
            spec = state.workflow_store.get_spec(workflow_id)
            state.workflow_builder.run_approved(spec, trigger={"type": "web_manual"})
        return RedirectResponse("/", status_code=303)

    @app.post("/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> RedirectResponse:
        if state.task_control is not None:
            state.task_control.request_cancel(task_id)
        return RedirectResponse("/", status_code=303)

    @app.post("/tasks/{task_id}/pause")
    async def pause_task(task_id: str) -> RedirectResponse:
        if state.task_control is not None:
            state.task_control.pause(task_id)
        return RedirectResponse("/", status_code=303)

    @app.post("/tasks/{task_id}/resume")
    async def resume_task(task_id: str) -> RedirectResponse:
        if state.task_control is not None:
            state.task_control.resume(task_id)
        return RedirectResponse("/", status_code=303)

    @app.post("/approvals/{approval_id}/approve")
    async def approve(approval_id: str) -> RedirectResponse:
        state.approvals.approve(approval_id)
        return RedirectResponse("/", status_code=303)

    @app.post("/approvals/{approval_id}/deny")
    async def deny(approval_id: str) -> RedirectResponse:
        state.approvals.deny(approval_id)
        return RedirectResponse("/", status_code=303)

    return app


def create_static_app(
    state_dir: str | Path,
    *,
    config: Any | None = None,
    source_discovery_model_id: str = "",
) -> FastAPI:
    trace = TraceLogger(Path(state_dir) / "web_trace.jsonl")
    from agentic.approvals.store import ApprovalStore

    approvals = ApprovalService(ApprovalStore(Path(state_dir) / "approvals.jsonl"), trace)
    workflow_store = WorkflowStore(Path(state_dir) / "workflows.sqlite3")
    planning_session_store = PlanningSessionStore(Path(state_dir) / "planning_sessions.sqlite3")
    session_log_store = SessionLogStore(Path(state_dir) / "sessions.sqlite3")
    tooling_store = ToolingBacklogStore(Path(state_dir) / "tooling.sqlite3")
    artifact_store = ArtifactStore(Path(state_dir) / "artifacts.sqlite3")
    source_store = SourceStore(Path(state_dir) / "sources.sqlite3")
    resource_store = ResourceStore(Path(state_dir) / "resources.sqlite3")
    task_store = TaskStore(Path(state_dir) / "agentic.sqlite3")
    skill_workshop = SkillWorkshopService(
        SkillWorkshopStore(Path(state_dir) / "skill_workshop.sqlite3"),
        skills_root=Path(state_dir) / "skills",
    )
    source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
    workflow_builder = WorkflowBuilder(
        WorkflowInterpreter(
            workflow_store=workflow_store,
            artifact_store=artifact_store,
            source_runtime=source_runtime,
            resource_store=resource_store,
            tooling_store=tooling_store,
            trace=trace,
        )
    )
    health_monitor = HealthMonitor(
        workflow_store=workflow_store,
        source_store=source_store,
        artifact_store=artifact_store,
        approvals=approvals,
    )
    return create_app(
        channel_loop=None,
        approvals=approvals,
        trace=trace,
        workflow_store=workflow_store,
        source_store=source_store,
        task_store=task_store,
        workflow_builder=workflow_builder,
        workflow_designer=WorkflowDesigner(),
        planning_session_store=planning_session_store,
        session_log_store=session_log_store,
        tooling_store=tooling_store,
        skill_workshop=skill_workshop,
        health_monitor=health_monitor,
        health_export_path=Path(state_dir) / "health_snapshot.json",
        workflow_lifecycle=WorkflowLifecycleService(
            workflow_store=workflow_store,
            source_store=source_store,
            schedule_store=ScheduleStore(Path(state_dir) / "schedules.sqlite3"),
            artifact_store=artifact_store,
            resource_store=resource_store,
            source_discovery_enqueuer=SourceDiscoveryEnqueuer(
                task_store=task_store,
                state_dir=state_dir,
                config_path=str(config.config_path) if config is not None else "config/config.toml",
                model_id=source_discovery_model_id
                or (config.runtime.default_subagent_model if config is not None else ""),
            ),
        ),
        delivery_store=DeliveryStore(Path(state_dir) / "deliveries.sqlite3"),
    )


def _task_records(task_store: TaskStore | None) -> list[dict[str, Any]]:
    if task_store is None:
        return []
    return [_task_record(task) for task in task_store.list_tasks(limit=20)]


def _task_record(task) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "kind": task.kind,
        "status": task.status.value,
        "input": task.input,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "last_heartbeat_at": task.last_heartbeat_at,
    }


def _workflow_records(workflow_store: WorkflowStore | None) -> list[dict[str, Any]]:
    if workflow_store is None:
        return []
    return [spec.to_record() for spec in workflow_store.list_specs(limit=20)]


def _workflow_run_records(workflow_store: WorkflowStore | None) -> list[dict[str, Any]]:
    if workflow_store is None:
        return []
    return [run.to_record() for run in workflow_store.list_runs(limit=20)]


def _planning_session_records(store: PlanningSessionStore | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    return [session.to_record() for session in store.list(limit=20)]


def _session_records(store: SessionLogStore | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    records: list[dict[str, Any]] = []
    for session in store.list_sessions(limit=20):
        record = session.to_record()
        record["event_count"] = len(store.list_events(session.session_id, limit=1000))
        records.append(record)
    return records


def _tooling_records(store: ToolingBacklogStore | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    return [request.to_record() for request in store.list(limit=20)]


def _skill_proposal_records(store: SkillWorkshopService | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    records = []
    for proposal in store.list(limit=20):
        record = proposal.to_record()
        try:
            record["review"] = store.review(proposal.proposal_id).to_record()
        except Exception as exc:
            record["review"] = {
                "validation_ok": False,
                "validation_error": f"{exc.__class__.__name__}: {exc}",
            }
        records.append(record)
    return records


def _delivery_records(store: DeliveryStore | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    return [delivery.to_record() for delivery in store.list(limit=20)]


def _daemon_record(runtime_daemon: RuntimeDaemonLoop | None) -> dict[str, Any] | None:
    if runtime_daemon is None:
        return None
    snapshot = runtime_daemon.snapshot()
    if isinstance(snapshot, dict):
        return snapshot
    return snapshot.to_record()


def _advance_workflow_lifecycle(state: WebState, workflow_id: str) -> dict[str, Any] | None:
    if state.workflow_lifecycle is None:
        return None
    result = state.workflow_lifecycle.advance_after_proposal(workflow_id)
    record = result.to_record()
    status = record.get("status")
    if result.ok:
        state.messages.append({"role": "agent", "text": f"Workflow activated: {workflow_id}"})
    else:
        state.messages.append(
            {
                "role": "agent",
                "text": f"Workflow lifecycle blocked: {status} {record.get('blockers')}",
            }
        )
    return record


def _start_design_session_log(state: WebState, message: str, planning_session) -> SessionRecord | None:
    if state.session_log_store is None:
        return None
    session = state.session_log_store.start_session(
        "workflow_design",
        metadata={
            "route": "workflows/design",
            "request": message,
            "planning_session_id": planning_session.session_id,
            "intent_type": planning_session.intent.intent_type.value,
        },
    )
    state.session_log_store.append_event(
        session.session_id,
        "user_request",
        role="user",
        content=message,
        payload={
            "planning_session_id": planning_session.session_id,
            "intent": planning_session.intent.to_record(),
            "extracted_slots": planning_session.extracted_slots,
        },
    )
    return session


def _find_session_log_by_planning_session(state: WebState, planning_session_id: str) -> SessionRecord | None:
    if state.session_log_store is None:
        return None
    for session in state.session_log_store.list_sessions(limit=200):
        metadata = session.metadata or {}
        if metadata.get("planning_session_id") == planning_session_id:
            return session
    return None


def _append_session_event(
    state: WebState,
    session: SessionRecord | None,
    event_type: str,
    *,
    role: str = "runtime",
    content: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    if state.session_log_store is None or session is None:
        return
    state.session_log_store.append_event(
        session.session_id,
        event_type,
        role=role,
        content=content,
        payload=payload or {},
    )


def _attach_session_log(
    spec: WorkflowSpec,
    *,
    session_log_id: str,
    planning_session_id: str,
) -> WorkflowSpec:
    if not session_log_id and not planning_session_id:
        return spec
    inputs = {
        **spec.inputs,
        "session_log_id": session_log_id,
        "planning_session_id": planning_session_id,
    }
    return replace(spec, inputs=inputs)


def _record_tooling_backlog(spec, store: ToolingBacklogStore | None) -> None:
    if store is None:
        return
    capability_plan = CapabilityPlanner().plan(spec)
    tooling_plan = ToolingPlanner().plan(capability_plan)
    store.add_many(tooling_plan.requests)
