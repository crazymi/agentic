from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from agentic.app.server import create_app
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactStore
from agentic.channels.ntfy import NtfyChannel, NtfyConfig
from agentic.config.settings import AppConfig
from agentic.delivery import DeliveryStore, ReportDeliveryService
from agentic.ops import HealthMonitor
from agentic.probes import WORKFLOW_BUILDER_PROBE_TASK_KIND, WorkflowBuilderProbeExecutor
from agentic.resources.store import ResourceStore
from agentic.runtime.channel_loop import ChannelLoop
from agentic.runtime.daemon import DurableRuntime, default_state_db
from agentic.runtime.daemon_loop import RuntimeDaemonLoop
from agentic.runtime.durable_channel_loop import ChatTurnExecutor, DurableChannelLoop
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.runtime.heartbeat import Watchdog
from agentic.runtime.task_router import TaskRouter
from agentic.runtime.task_control import TaskControl
from agentic.runtime.tick import RuntimeTickService
from agentic.scheduler import ScheduleStore, SchedulerRunner
from agentic.sessions import SessionLogStore
from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore
from agentic.sources import SourceRuntime, SourceStore
from agentic.sources.discovery import (
    SOURCE_DISCOVERY_TASK_KIND,
    SourceDiscoveryEnqueuer,
    SourceDiscoveryExecutor,
)
from agentic.sources.strategy_recovery import (
    SOURCE_STRATEGY_RECOVERY_TASK_KIND,
    SourceStrategyRecoveryEnqueuer,
    SourceStrategyRecoveryExecutor,
)
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger
from agentic.tooling import ToolingBacklogStore
from agentic.workflow_kernel import (
    PlanningSessionStore,
    WorkflowBuilder,
    WorkflowDesigner,
    WorkflowInterpreter,
    WorkflowLifecycleService,
    WorkflowStore,
)


def create_channel_app(
    config: AppConfig,
    *,
    daemon_interval_s: float = 10.0,
    daemon_tick_timeout_s: float = 120.0,
    ntfy_enabled: bool = False,
    ntfy_topic: str = "",
    ntfy_server: str = "https://ntfy.sh",
    web_url: str = "http://127.0.0.1:8765",
) -> FastAPI:
    trace = TraceLogger(config.runtime.trace_file)
    runtime = FullLoopRuntime.from_config(config)
    channel_loop = ChannelLoop(runtime=runtime, trace=trace)
    approvals = ApprovalService(_approval_store(config), trace=trace)
    state_dir = config.trace_dir / "state"
    executor = TaskRouter(
        {
            "chat_turn": ChatTurnExecutor(
                lambda: FullLoopRuntime.from_config(config, state_dir=state_dir)
            ),
            WORKFLOW_BUILDER_PROBE_TASK_KIND: WorkflowBuilderProbeExecutor(
                config=config,
                state_dir=state_dir,
            ),
            SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                default_state_dir=state_dir,
            ),
            SOURCE_DISCOVERY_TASK_KIND: SourceDiscoveryExecutor(
                config=config,
                default_state_dir=state_dir,
            ),
        }
    )
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
    workflow_store = WorkflowStore(_workflow_db(config))
    planning_session_store = PlanningSessionStore(_planning_session_db(config))
    session_log_store = SessionLogStore(state_dir / "sessions.sqlite3")
    tooling_store = ToolingBacklogStore(_tooling_db(config))
    skill_workshop = SkillWorkshopService(
        SkillWorkshopStore(config.trace_dir / "state" / "skill_workshop.sqlite3"),
        skills_root="skills",
    )
    artifact_store = ArtifactStore(_artifact_db(config))
    source_store = SourceStore(_source_db(config))
    resource_store = ResourceStore(_resource_db(config))
    source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
    delivery_store = DeliveryStore(state_dir / "deliveries.sqlite3")
    ntfy_channel = (
        NtfyChannel(
            NtfyConfig(
                enabled=True,
                server=ntfy_server,
                topic=ntfy_topic,
                title="Agentic report ready",
                web_url=web_url,
            )
        )
        if ntfy_enabled and ntfy_topic
        else None
    )
    workflow_builder = WorkflowBuilder(
        WorkflowInterpreter(
            workflow_store=workflow_store,
            artifact_store=artifact_store,
            source_runtime=source_runtime,
            resource_store=resource_store,
            tooling_store=tooling_store,
            trace=trace,
            source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                task_store=durable.store,
                state_dir=state_dir,
            ),
        )
    )
    scheduler = SchedulerRunner(
        schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
        workflow_store=workflow_store,
        builder=workflow_builder,
    )
    runtime_daemon = RuntimeDaemonLoop(
        tick_service=RuntimeTickService(
            task_pool=durable.pool,
            watchdog=Watchdog(durable.store, trace=trace),
            scheduler=scheduler,
            report_delivery=ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=ntfy_channel,
                web_url=web_url,
            ),
        ),
        interval_s=daemon_interval_s,
        tick_timeout_s=daemon_tick_timeout_s,
        wait_for_tasks=False,
    )
    health_monitor = HealthMonitor(
        task_store=durable.store,
        task_pool=durable.pool,
        workflow_store=workflow_store,
        source_store=source_store,
        artifact_store=artifact_store,
        approvals=approvals,
    )
    app = create_app(
        channel_loop=channel_loop,
        durable_channel_loop=durable_channel_loop,
        approvals=approvals,
        trace=trace,
        task_store=durable.store,
        task_control=task_control,
        workflow_store=workflow_store,
        source_store=source_store,
        workflow_builder=workflow_builder,
        workflow_designer=WorkflowDesigner(),
        workflow_lifecycle=WorkflowLifecycleService(
            workflow_store=workflow_store,
            source_store=source_store,
            schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
            artifact_store=artifact_store,
            resource_store=resource_store,
            tooling_store=tooling_store,
            source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                task_store=durable.store,
                state_dir=state_dir,
            ),
            source_discovery_enqueuer=SourceDiscoveryEnqueuer(
                task_store=durable.store,
                state_dir=state_dir,
                config_path=str(config.config_path),
                model_id=config.runtime.default_subagent_model,
            ),
        ),
        planning_session_store=planning_session_store,
        session_log_store=session_log_store,
        tooling_store=tooling_store,
        skill_workshop=skill_workshop,
        health_monitor=health_monitor,
        health_export_path=config.trace_dir / "state" / "health_snapshot.json",
        delivery_store=delivery_store,
        runtime_daemon=runtime_daemon,
    )

    @app.on_event("startup")
    async def _startup() -> None:
        durable.start()
        runtime_daemon.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        runtime_daemon.stop()
        durable.shutdown()

    return app


def _approval_store(config: AppConfig) -> ApprovalStore:
    return ApprovalStore(Path(config.trace_dir / "state") / "approvals.jsonl")


def _task_store(config: AppConfig) -> TaskStore:
    return TaskStore(default_state_db(config))


def _workflow_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "workflows.sqlite3"


def _planning_session_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "planning_sessions.sqlite3"


def _tooling_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "tooling.sqlite3"


def _artifact_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "artifacts.sqlite3"


def _source_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "sources.sqlite3"


def _resource_db(config: AppConfig) -> Path:
    return config.trace_dir / "state" / "resources.sqlite3"
