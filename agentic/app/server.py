from __future__ import annotations

from pathlib import Path
from typing import Any

from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agentic.app.web_templates import render_home
from agentic.approvals.service import ApprovalService
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.events import InboundMessage
from agentic.traces.logger import TraceLogger


class WebState:
    def __init__(
        self,
        *,
        channel_loop: ChannelLoop | None,
        approvals: ApprovalService,
        trace: TraceLogger,
    ):
        self.channel_loop = channel_loop
        self.approvals = approvals
        self.trace = trace
        self.messages: list[dict[str, Any]] = []


def create_app(
    *,
    channel_loop: ChannelLoop | None,
    approvals: ApprovalService,
    trace: TraceLogger,
) -> FastAPI:
    app = FastAPI(title="agentic")
    state = WebState(channel_loop=channel_loop, approvals=approvals, trace=trace)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> str:
        return render_home(
            messages=state.messages,
            approvals=[item.to_record() for item in state.approvals.get_pending()],
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
        if state.channel_loop is None:
            response_text = "Channel loop is not configured."
        else:
            response = state.channel_loop.handle_message(inbound)
            response_text = response.text
        state.messages.append({"role": "agent", "text": response_text})
        return RedirectResponse("/", status_code=303)

    @app.get("/approvals")
    async def list_approvals() -> list[dict[str, Any]]:
        return [item.to_record() for item in state.approvals.get_pending()]

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
    return create_app(channel_loop=None, approvals=approvals, trace=trace)
