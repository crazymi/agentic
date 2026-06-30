from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.config.settings import AppConfig
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.traces.logger import TraceLogger


def create_channel_app(config: AppConfig) -> FastAPI:
    trace = TraceLogger(config.runtime.trace_file)
    runtime = FullLoopRuntime.from_config(config)
    channel_loop = ChannelLoop(runtime=runtime, trace=trace)
    approvals = ApprovalService(_approval_store(config), trace=trace)
    return create_app(channel_loop=channel_loop, approvals=approvals, trace=trace)


def _approval_store(config: AppConfig) -> ApprovalStore:
    state_dir = config.trace_dir / "state"
    return ApprovalStore(Path(state_dir) / "approvals.jsonl")
