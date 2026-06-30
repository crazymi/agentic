from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.config.settings import AppConfig
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.daemon import DurableRuntime, default_state_db
from agentic.runtime.durable_channel_loop import ChatTurnExecutor, DurableChannelLoop
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.runtime.task_control import TaskControl
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


def create_channel_app(config: AppConfig) -> FastAPI:
    trace = TraceLogger(config.runtime.trace_file)
    runtime = FullLoopRuntime.from_config(config)
    channel_loop = ChannelLoop(runtime=runtime, trace=trace)
    approvals = ApprovalService(_approval_store(config), trace=trace)
    executor = ChatTurnExecutor(lambda: FullLoopRuntime.from_config(config))
    durable = DurableRuntime.from_config(
        config,
        executor=executor,
        trace=trace,
        max_workers=1,
    )
    task_control = TaskControl(durable.store)
    durable_channel_loop = DurableChannelLoop(
        store=durable.store,
        pool=durable.pool,
        trace=trace,
    )
    app = create_app(
        channel_loop=channel_loop,
        durable_channel_loop=durable_channel_loop,
        approvals=approvals,
        trace=trace,
        task_store=durable.store,
        task_control=task_control,
    )

    @app.on_event("startup")
    async def _startup() -> None:
        durable.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        durable.shutdown()

    return app


def _approval_store(config: AppConfig) -> ApprovalStore:
    state_dir = config.trace_dir / "state"
    return ApprovalStore(Path(state_dir) / "approvals.jsonl")


def _task_store(config: AppConfig) -> TaskStore:
    return TaskStore(default_state_db(config))
