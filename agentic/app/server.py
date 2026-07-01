from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agentic.app.web_templates import render_home
from agentic.artifacts import ArtifactStore
from agentic.approvals.service import ApprovalService
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.durable_channel_loop import DurableChannelLoop
from agentic.runtime.events import InboundMessage
from agentic.runtime.task_control import TaskControl
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel import (
    WorkflowBuilder,
    WorkflowDesigner,
    WorkflowInterpreter,
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
        workflow_builder: WorkflowBuilder | None,
        workflow_designer: WorkflowDesigner | None,
    ):
        self.channel_loop = channel_loop
        self.durable_channel_loop = durable_channel_loop
        self.approvals = approvals
        self.trace = trace
        self.task_store = task_store
        self.task_control = task_control
        self.workflow_store = workflow_store
        self.workflow_builder = workflow_builder
        self.workflow_designer = workflow_designer
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
    workflow_builder: WorkflowBuilder | None = None,
    workflow_designer: WorkflowDesigner | None = None,
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
        workflow_builder=workflow_builder,
        workflow_designer=workflow_designer,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> str:
        return render_home(
            messages=state.messages,
            approvals=[item.to_record() for item in state.approvals.get_pending()],
            tasks=_task_records(state.task_store),
            workflows=_workflow_records(state.workflow_store),
            workflow_runs=_workflow_run_records(state.workflow_store),
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

    @app.post("/workflows/design")
    async def design_workflow(request: Request) -> RedirectResponse:
        if state.workflow_designer is None or state.workflow_store is None:
            state.messages.append({"role": "agent", "text": "Workflow designer is not configured."})
            return RedirectResponse("/", status_code=303)
        body = (await request.body()).decode("utf-8")
        message = parse_qs(body).get("message", [""])[0]
        proposal = state.workflow_designer.design(message)
        if proposal.spec is not None:
            state.workflow_store.create_spec(proposal.spec)
        state.messages.append({"role": "user", "text": message})
        state.messages.append({"role": "agent", "text": proposal.to_markdown()})
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/approve")
    async def approve_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.APPROVED)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/activate")
    async def activate_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.ACTIVE)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/pause")
    async def pause_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_store is not None:
            state.workflow_store.transition_spec(workflow_id, WorkflowStatus.PAUSED)
        return RedirectResponse("/", status_code=303)

    @app.post("/workflows/{workflow_id}/run")
    async def run_workflow(workflow_id: str) -> RedirectResponse:
        if state.workflow_store is not None and state.workflow_builder is not None:
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


def create_static_app(state_dir: str | Path) -> FastAPI:
    trace = TraceLogger(Path(state_dir) / "web_trace.jsonl")
    from agentic.approvals.store import ApprovalStore

    approvals = ApprovalService(ApprovalStore(Path(state_dir) / "approvals.jsonl"), trace)
    workflow_store = WorkflowStore(Path(state_dir) / "workflows.sqlite3")
    artifact_store = ArtifactStore(Path(state_dir) / "artifacts.sqlite3")
    workflow_builder = WorkflowBuilder(
        WorkflowInterpreter(
            workflow_store=workflow_store,
            artifact_store=artifact_store,
            trace=trace,
        )
    )
    return create_app(
        channel_loop=None,
        approvals=approvals,
        trace=trace,
        workflow_store=workflow_store,
        workflow_builder=workflow_builder,
        workflow_designer=WorkflowDesigner(),
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
