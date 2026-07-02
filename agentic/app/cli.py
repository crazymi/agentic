from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactStore
from agentic.benchmarks import RealBenchmarkOptions, run_real_benchmark
from agentic.config.settings import AppConfig, load_app_config
from agentic.channels.ntfy import NtfyChannel, NtfyConfig
from agentic.delivery import DeliveryStore, ReportDeliveryService
from agentic.experience import ExperienceStore, run_requirement_smoke
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.ops import HealthMonitor, run_operational_smoke
from agentic.probes import (
    DEFAULT_PROBE_ANSWERS,
    DEFAULT_PROBE_REQUEST,
    WORKFLOW_BUILDER_PROBE_TASK_KIND,
    WORKFLOW_SPEC_PROBE_TASK_KIND,
    WorkflowBuilderProbeExecutor,
    WorkflowSpecProbeExecutor,
    run_workflow_builder_probe,
    run_workflow_spec_probe,
)
from agentic.probes.finish_line import (
    DEFAULT_FINISH_LINE_ALIASES,
    DEFAULT_FINISH_LINE_ANSWERS,
    DEFAULT_FINISH_LINE_REQUEST,
    DEFAULT_FINISH_LINE_SOURCE_URL,
    run_frontdoor_finish_line_benchmark,
)
from agentic.prompts.builder import PromptBuilder
from agentic.app.chat import run_chat_once, run_chat_repl
from agentic.runtime.preflight import run_preflight
from agentic.runtime.daemon import default_state_db, recover_interrupted_tasks
from agentic.runtime.daemon_loop import RuntimeDaemonLoop
from agentic.runtime.heartbeat import Watchdog
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.task_router import TaskRouter
from agentic.runtime.tick import RuntimeTickService
from agentic.resources.store import ResourceStore
from agentic.scheduler import ScheduleStore, SchedulerRunner
from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.sources.discovery import (
    SOURCE_DISCOVERY_TASK_KIND,
    SourceDiscoveryEnqueuer,
    SourceDiscoveryExecutor,
)
from agentic.sources.strategy_workshop import (
    SourceStrategyProposalStore,
    SourceStrategyWorkshopService,
)
from agentic.sources.strategy_recovery import (
    SOURCE_STRATEGY_RECOVERY_TASK_KIND,
    SourceStrategyRecoveryEnqueuer,
    SourceStrategyRecoveryExecutor,
    build_source_strategy_recovery_service,
)
from agentic.synthesis.resources import summarize_resource_trends
from agentic.tasks.store import TaskStore
from agentic.tasks.state_machine import TERMINAL_STATUSES
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger
from agentic.tooling import ToolingBacklogStore
from agentic.workflow_kernel import WorkflowBuilder, WorkflowInterpreter, WorkflowStore
from agentic.workflow_kernel.lifecycle import WorkflowLifecycleService


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal local GGUF agent harness")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--config", default="config/config.toml", help="path to config.toml")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("config-check", help="validate config, prompts, and model paths")
    subparsers.add_parser("list-models", help="list configured local models")
    subparsers.add_parser("runner-check", help="check local runner build/runtime prerequisites")
    subparsers.add_parser("ops-status", help="print operational health snapshot JSON")
    ops_smoke = subparsers.add_parser("ops-smoke", help="run operational smoke checks")
    ops_smoke.add_argument("--state-dir", default="", help="optional state directory for smoke stores")
    ops_smoke.add_argument("--include-model", action="store_true", help="also run a real configured model smoke")
    ops_smoke.add_argument("--model", default="", help="model id for --include-model")
    ops_smoke.add_argument("--model-max-tokens", type=int, default=0, help="override model max tokens for --include-model")
    ops_smoke.add_argument("--prompt", default="한국의 수도는 어디야? 답변만 한 문장으로 말해.", help="model smoke prompt")
    req_smoke = subparsers.add_parser("requirements-smoke", help="run user-requirement harness probes")
    req_smoke.add_argument("--state-dir", default="", help="optional state directory for requirement smoke stores")
    req_smoke.add_argument("--experience-path", default="", help="optional JSONL experience log path")
    req_smoke.add_argument(
        "--no-persist-experience",
        action="store_true",
        help="do not append probe results to the experience log",
    )
    exp_list = subparsers.add_parser("experience-list", help="print recent experience events")
    exp_list.add_argument("--experience-path", default="", help="optional JSONL experience log path")
    exp_list.add_argument("--limit", type=int, default=20, help="number of events to print")
    real_bench = subparsers.add_parser("real-bench", help="run live user-requirement benchmarks only")
    real_bench.add_argument("--state-dir", default="", help="state directory for benchmark stores")
    real_bench.add_argument("--experience-path", default="", help="optional JSONL experience log path")
    real_bench.add_argument("--no-persist-experience", action="store_true", help="do not append results to experience")
    real_bench.add_argument("--skip-network", action="store_true", help="skip live web crawls")
    real_bench.add_argument("--skip-ntfy", action="store_true", help="skip real ntfy delivery probe")
    real_bench.add_argument("--skip-model", action="store_true", help="skip real local model execution")
    real_bench.add_argument("--model", default="", help="model id for real local model execution")
    real_bench.add_argument("--model-max-tokens", type=int, default=256, help="max tokens for model probe")
    real_bench.add_argument("--prompt", default="한국의 수도는 어디야? 답변만 한 문장으로 말해.", help="model prompt")
    real_bench.add_argument("--reddit-url", default="", help="Reddit JSON URL to crawl")
    real_bench.add_argument("--dcinside-url", default="", help="DCInside gallery URL to crawl")
    real_bench.add_argument("--ticket-url", default="", help="official ticket URL for live browser transaction probe")
    finish_line = subparsers.add_parser(
        "finish-line-bench",
        help="run a real front-door vague-request benchmark through workflow delivery",
    )
    finish_line.add_argument("--state-dir", default="", help="state directory for benchmark stores")
    finish_line.add_argument("--request", default=DEFAULT_FINISH_LINE_REQUEST, help="vague request to send")
    finish_line.add_argument(
        "--answer",
        action="append",
        default=[],
        help="interview answer; pass multiple times. Defaults to the social-trend probe answers.",
    )
    finish_line.add_argument("--source-url", default=DEFAULT_FINISH_LINE_SOURCE_URL, help="real source URL")
    finish_line.add_argument("--source-name", default="Live DCInside stock gallery", help="source display name")
    finish_line.add_argument(
        "--source-alias",
        action="append",
        default=[],
        help="source alias used for workflow binding; pass multiple times",
    )
    finish_line.add_argument("--ntfy-topic", default="", help="ntfy topic required for delivery verification")
    finish_line.add_argument("--ntfy-server", default="https://ntfy.sh", help="ntfy server URL")
    finish_line.add_argument("--web-url", default="http://127.0.0.1:8765", help="local web URL in report delivery")
    finish_line.add_argument("--timeout-s", type=float, default=120.0, help="runtime tick timeout")
    finish_line.add_argument(
        "--synthesis-model",
        default="",
        help="optional configured local model id for report synthesis",
    )
    finish_line.add_argument(
        "--synthesis-max-tokens",
        type=int,
        default=384,
        help="max tokens for optional report synthesis model call",
    )
    finish_line.add_argument(
        "--require-model-synthesis",
        action="store_true",
        help="require grounded model-assisted report synthesis for a 100/100 finish-line pass",
    )
    finish_line.add_argument(
        "--allow-no-delivery",
        action="store_true",
        help="developer-only: allow artifact success without sent ntfy delivery",
    )
    finish_line.add_argument(
        "--no-preseed-source",
        action="store_true",
        help="do not register any source before the request; requires source_discovery to find and bind one",
    )
    finish_line.add_argument(
        "--source-discovery-model",
        default="",
        help="optional configured model id for source discovery tasks",
    )
    web_collect = subparsers.add_parser("web-collect", help="collect a real web page into ResourceStore")
    web_collect.add_argument("--url", required=True, help="real URL to fetch")
    web_collect.add_argument("--name", default="Live web collection", help="source name")
    web_collect.add_argument("--href-contains", action="append", default=[], help="keep links whose href contains this text")
    web_collect.add_argument(
        "--href-contains-all",
        action="append",
        default=[],
        help="keep links only when href contains all provided fragments",
    )
    web_collect.add_argument("--href-excludes", action="append", default=[], help="drop links whose href contains this text")
    web_collect.add_argument("--text-excludes", action="append", default=[], help="drop links whose text contains this text")
    web_collect.add_argument("--text-exclude-regex", action="append", default=[], help="drop links whose text matches this regex")
    web_collect.add_argument("--min-text-chars", type=int, default=0, help="drop extracted links with shorter visible text")
    web_collect.add_argument("--limit", type=int, default=20, help="maximum extracted link resources")
    web_collect.add_argument("--state-dir", default="", help="state directory for source/resource stores")
    sources_cmd = subparsers.add_parser("sources", help="manage enabled source definitions")
    sources_cmd.add_argument("action", choices=["add-web", "list", "collect"], help="source action")
    sources_cmd.add_argument("--state-dir", default="", help="state directory for source/resource stores")
    sources_cmd.add_argument("--source-id", default="", help="source id for collect")
    sources_cmd.add_argument("--url", default="", help="web source URL for add-web")
    sources_cmd.add_argument("--name", default="", help="source name for add-web")
    sources_cmd.add_argument("--alias", action="append", default=[], help="alias used for workflow source binding")
    sources_cmd.add_argument("--href-contains", action="append", default=[], help="keep links whose href contains this text")
    sources_cmd.add_argument(
        "--href-contains-all",
        action="append",
        default=[],
        help="keep links only when href contains all provided fragments",
    )
    sources_cmd.add_argument("--href-excludes", action="append", default=[], help="drop links whose href contains this text")
    sources_cmd.add_argument("--text-excludes", action="append", default=[], help="drop links whose text contains this text")
    sources_cmd.add_argument("--text-exclude-regex", action="append", default=[], help="drop links whose text matches this regex")
    sources_cmd.add_argument("--min-text-chars", type=int, default=0, help="drop extracted links with shorter visible text")
    sources_cmd.add_argument("--limit", type=int, default=20, help="maximum extracted link resources")
    source_discovery = subparsers.add_parser("source-discovery", help="retry agent source discovery with user feedback")
    source_discovery.add_argument("action", choices=["retry"], help="source discovery action")
    source_discovery.add_argument("--state-dir", default="", help="state directory containing workflow/task stores")
    source_discovery.add_argument("--workflow-id", required=True, help="workflow id needing source discovery")
    source_discovery.add_argument(
        "--feedback",
        required=True,
        help="user/operator feedback to pass to the source-discovery agent without adding URLs or source secrets",
    )
    source_discovery.add_argument("--model", default="", help="optional configured model id for the retry")
    tooling_cmd = subparsers.add_parser("tooling", help="inspect tooling backlog requests")
    tooling_cmd.add_argument("action", choices=["list"], help="tooling action")
    tooling_cmd.add_argument("--state-dir", default="", help="state directory containing tooling.sqlite3")
    tooling_cmd.add_argument("--workflow-id", default="", help="optional workflow id filter")
    tooling_cmd.add_argument("--status", default="", help="optional status filter")
    tooling_cmd.add_argument("--limit", type=int, default=50, help="list limit")
    source_strategy = subparsers.add_parser(
        "source-strategy",
        help="manage source strategy proposals created from quality failures",
    )
    source_strategy.add_argument(
        "action",
        choices=[
            "propose",
            "list",
            "inspect",
            "apply",
            "reject",
            "recover",
            "recover-pending",
            "recover-task",
            "kick-recovery",
        ],
        help="source strategy action",
    )
    source_strategy.add_argument("--state-dir", default="", help="state directory containing source/tooling stores")
    source_strategy.add_argument("--tooling-id", default="", help="source:strategy_tuning tooling id")
    source_strategy.add_argument("--proposal-id", default="", help="source strategy proposal id")
    source_strategy.add_argument("--source-id", default="", help="optional source id filter")
    source_strategy.add_argument("--status", default="", help="optional proposal status filter")
    source_strategy.add_argument("--limit", type=int, default=50, help="list limit")
    source_strategy.add_argument("--no-auto-apply", action="store_true", help="create proposals but do not auto-apply safe patches")
    source_strategy.add_argument("--no-rerun", action="store_true", help="do not rerun workflow after applying a patch")
    source_strategy.add_argument("--timeout-s", type=float, default=120.0, help="task wait timeout")
    source_strategy.add_argument("--no-wait", action="store_true", help="enqueue recovery task only and return immediately")
    trends = subparsers.add_parser("resource-trends", help="summarize terms from ResourceStore")
    trends.add_argument("--state-dir", default="", help="state directory containing resources.sqlite3")
    trends.add_argument("--query", default="", help="optional resource text/title query")
    trends.add_argument("--limit", type=int, default=100, help="recent resource limit")
    trends.add_argument("--top-n", type=int, default=20, help="number of top terms")
    skill_workshop = subparsers.add_parser("skill-workshop", help="manage pending skill proposals")
    skill_workshop.add_argument(
        "action",
        choices=[
            "create",
            "list",
            "inspect",
            "review",
            "reject",
            "quarantine",
            "request-apply",
            "apply",
        ],
        help="proposal action",
    )
    skill_workshop.add_argument("--name", default="", help="skill proposal name for create")
    skill_workshop.add_argument("--description", default="", help="short proposal description for create")
    skill_workshop.add_argument("--proposal-body", default="", help="proposal body text for create")
    skill_workshop.add_argument("--proposal-file", default="", help="read proposal body from file for create")
    skill_workshop.add_argument("--proposal-id", default="", help="proposal id for inspect/reject/quarantine")
    skill_workshop.add_argument("--approval-id", default="", help="approval id for apply")
    skill_workshop.add_argument("--reason", default="", help="reason for reject/quarantine")
    skill_workshop.add_argument("--status", default="", help="optional list status filter")
    skill_workshop.add_argument("--limit", type=int, default=20, help="list limit")
    skill_workshop.add_argument("--state-dir", default="", help="state directory for skill workshop store")
    skill_workshop.add_argument("--skills-root", default="skills", help="active skills root")
    approvals_cmd = subparsers.add_parser("approvals", help="manage approval requests")
    approvals_cmd.add_argument("action", choices=["list", "approve", "deny"], help="approval action")
    approvals_cmd.add_argument("--approval-id", default="", help="approval id for approve/deny")
    approvals_cmd.add_argument("--state-dir", default="", help="state directory for approvals store")
    harness_probe = subparsers.add_parser(
        "harness-probe",
        help="run one general workflow-building harness probe",
    )
    harness_probe.add_argument("--request", default=DEFAULT_PROBE_REQUEST, help="vague user request to probe")
    harness_probe.add_argument(
        "--answer",
        action="append",
        default=[],
        help="answer to an interview question; can be passed multiple times",
    )
    harness_probe.add_argument("--state-dir", default="", help="state directory for probe stores")
    harness_probe_task = subparsers.add_parser(
        "harness-probe-task",
        help="enqueue and run the workflow-building harness probe as a durable task",
    )
    harness_probe_task.add_argument("--request", default=DEFAULT_PROBE_REQUEST, help="vague user request to probe")
    harness_probe_task.add_argument(
        "--answer",
        action="append",
        default=[],
        help="answer to an interview question; can be passed multiple times",
    )
    harness_probe_task.add_argument("--state-dir", default="", help="state directory for durable task/probe stores")
    harness_probe_task.add_argument("--timeout-s", type=float, default=900.0, help="wait timeout")
    harness_probe_task.add_argument("--no-wait", action="store_true", help="enqueue only and return immediately")
    workflow_spec_probe = subparsers.add_parser(
        "harness-workflow-spec-probe",
        help="run one general workflow-spec generation harness probe",
    )
    workflow_spec_probe.add_argument("--request", default=DEFAULT_PROBE_REQUEST, help="vague user request to probe")
    workflow_spec_probe.add_argument(
        "--answer",
        action="append",
        default=[],
        help="answer to an interview question; can be passed multiple times",
    )
    workflow_spec_probe.add_argument("--state-dir", default="", help="state directory for probe stores")
    workflow_spec_probe_task = subparsers.add_parser(
        "harness-workflow-spec-probe-task",
        help="enqueue and run the workflow-spec harness probe as a durable task",
    )
    workflow_spec_probe_task.add_argument("--request", default=DEFAULT_PROBE_REQUEST, help="vague user request to probe")
    workflow_spec_probe_task.add_argument(
        "--answer",
        action="append",
        default=[],
        help="answer to an interview question; can be passed multiple times",
    )
    workflow_spec_probe_task.add_argument("--state-dir", default="", help="state directory for durable task/probe stores")
    workflow_spec_probe_task.add_argument("--timeout-s", type=float, default=900.0, help="wait timeout")
    workflow_spec_probe_task.add_argument("--no-wait", action="store_true", help="enqueue only and return immediately")
    workflow_lifecycle = subparsers.add_parser(
        "workflow-lifecycle",
        help="review, bind, approve, activate, or run a WorkflowSpec through runtime gates",
    )
    workflow_lifecycle.add_argument(
        "action",
        choices=["review", "bind-sources", "approve", "activate", "run", "events"],
        help="lifecycle action",
    )
    workflow_lifecycle.add_argument("--workflow-id", required=True, help="workflow id")
    workflow_lifecycle.add_argument("--state-dir", default="", help="state directory containing workflow stores")
    workflow_lifecycle.add_argument("--limit", type=int, default=100, help="event list limit")
    scheduler_due = subparsers.add_parser("scheduler-run-due", help="run due active workflow schedules once")
    scheduler_due.add_argument("--state-dir", default="", help="state directory containing scheduler stores")
    scheduler_due.add_argument("--now", default="", help="optional ISO timestamp for due scan")

    runtime_tick = subparsers.add_parser("runtime-tick", help="run one durable runtime tick")
    runtime_tick.add_argument("--state-dir", default="", help="state directory containing runtime stores")
    runtime_tick.add_argument("--timeout-s", type=float, default=120.0, help="wait timeout for task pool")
    runtime_tick.add_argument("--no-wait", action="store_true", help="do not wait for submitted tasks to finish")
    runtime_tick.add_argument("--ntfy-enabled", action="store_true", help="send pending report deliveries through ntfy")
    runtime_tick.add_argument("--ntfy-topic", default="", help="ntfy topic for report delivery")
    runtime_tick.add_argument("--ntfy-server", default="https://ntfy.sh", help="ntfy server URL")
    runtime_tick.add_argument("--web-url", default="http://127.0.0.1:8765", help="local web URL to include in reports")

    runtime_daemon = subparsers.add_parser("runtime-daemon", help="run the durable runtime loop")
    runtime_daemon.add_argument("--state-dir", default="", help="state directory containing runtime stores")
    runtime_daemon.add_argument("--duration-s", type=float, default=0.0, help="run for this many seconds, or forever when 0")
    runtime_daemon.add_argument("--interval-s", type=float, default=10.0, help="daemon tick interval")
    runtime_daemon.add_argument("--timeout-s", type=float, default=120.0, help="wait timeout for one tick")
    runtime_daemon.add_argument("--wait-for-tasks", action="store_true", help="wait for task pool idle inside each tick")
    runtime_daemon.add_argument("--ntfy-enabled", action="store_true", help="send pending report deliveries through ntfy")
    runtime_daemon.add_argument("--ntfy-topic", default="", help="ntfy topic for report delivery")
    runtime_daemon.add_argument("--ntfy-server", default="https://ntfy.sh", help="ntfy server URL")
    runtime_daemon.add_argument("--web-url", default="http://127.0.0.1:8765", help="local web URL to include in reports")

    ask = subparsers.add_parser("ask", help="run one full-loop agent turn")
    ask.add_argument("message", nargs="+", help="message to send to the full-loop runtime")

    subparsers.add_parser("chat", help="start a simple full-loop chat REPL")

    serve = subparsers.add_parser("serve", help="start the local web channel")
    serve.add_argument("--host", default="127.0.0.1", help="bind host")
    serve.add_argument("--port", type=int, default=8765, help="bind port")
    serve.add_argument("--daemon-interval-s", type=float, default=10.0, help="background runtime tick interval")
    serve.add_argument("--daemon-timeout-s", type=float, default=120.0, help="background runtime tick timeout")
    serve.add_argument("--ntfy-enabled", action="store_true", help="send report deliveries through ntfy")
    serve.add_argument("--ntfy-topic", default="", help="ntfy topic for report delivery")
    serve.add_argument("--ntfy-server", default="https://ntfy.sh", help="ntfy server URL")

    smoke = subparsers.add_parser("smoke", help="run one model smoke call")
    smoke.add_argument("--model", default="", help="configured model id")
    smoke.add_argument("--prompt", default="hello from phase 0", help="prompt text")
    smoke.add_argument("--max-tokens", type=int, default=0, help="override configured max tokens")

    args = parser.parse_args()

    if args.version:
        from agentic import __version__

        print(__version__)
        return

    if not args.command:
        parser.print_help()
        return

    config = load_app_config(args.config)
    if args.command == "config-check":
        _config_check(config)
        return
    if args.command == "list-models":
        _list_models(config)
        return
    if args.command == "runner-check":
        _runner_check(config)
        return
    if args.command == "ops-status":
        _ops_status(config)
        return
    if args.command == "ops-smoke":
        _ops_smoke(config, args.state_dir, args.include_model, args.model, args.model_max_tokens, args.prompt)
        return
    if args.command == "requirements-smoke":
        _requirements_smoke(
            config,
            args.state_dir,
            args.experience_path,
            not args.no_persist_experience,
        )
        return
    if args.command == "experience-list":
        _experience_list(config, args.experience_path, args.limit)
        return
    if args.command == "real-bench":
        _real_bench(config, args)
        return
    if args.command == "finish-line-bench":
        _finish_line_bench(config, args)
        return
    if args.command == "web-collect":
        _web_collect(config, args)
        return
    if args.command == "sources":
        _sources(config, args)
        return
    if args.command == "source-discovery":
        _source_discovery(config, args)
        return
    if args.command == "tooling":
        _tooling(config, args)
        return
    if args.command == "source-strategy":
        _source_strategy(config, args)
        return
    if args.command == "resource-trends":
        _resource_trends(config, args)
        return
    if args.command == "skill-workshop":
        _skill_workshop(config, args)
        return
    if args.command == "approvals":
        _approvals(config, args)
        return
    if args.command == "harness-probe":
        _harness_probe(config, args)
        return
    if args.command == "harness-probe-task":
        _harness_probe_task(config, args)
        return
    if args.command == "harness-workflow-spec-probe":
        _harness_workflow_spec_probe(config, args)
        return
    if args.command == "harness-workflow-spec-probe-task":
        _harness_workflow_spec_probe_task(config, args)
        return
    if args.command == "workflow-lifecycle":
        _workflow_lifecycle(config, args)
        return
    if args.command == "scheduler-run-due":
        _scheduler_run_due(config, args)
        return
    if args.command == "runtime-tick":
        _runtime_tick(config, args)
        return
    if args.command == "runtime-daemon":
        _runtime_daemon(config, args)
        return
    if args.command == "ask":
        print(run_chat_once(config, " ".join(args.message)))
        return
    if args.command == "chat":
        run_chat_repl(config)
        return
    if args.command == "serve":
        _serve(config, args)
        return
    if args.command == "smoke":
        _smoke(config, args.model, args.prompt, args.max_tokens)
        return


def _config_check(config: AppConfig) -> None:
    print(f"config: {config.config_path}")
    print(f"package_manager: {config.package_manager}")
    print(f"venv: {_status(config.venv)} {config.venv}")
    print(f"prompt_dir: {_status(config.prompt_dir)} {config.prompt_dir}")
    print(f"model_dir: {_status(config.model_dir)} {config.model_dir}")
    print(f"trace_dir: {config.trace_dir}")
    print(f"prompt.master: {_status(config.prompts.master)} {config.prompts.master}")
    print(f"prompt.subagent: {_status(config.prompts.subagent)} {config.prompts.subagent}")
    print(
        "prompt.tool_call_grammar: "
        f"{_status(config.prompts.tool_call_grammar)} {config.prompts.tool_call_grammar}"
    )
    for model_id, model in config.models.items():
        executable_status = _status(Path(model.executable)) if model.executable else "missing"
        print(
            f"model.{model_id}: role={model.role} "
            f"model_path={_status(Path(model.model_path))} "
            f"executable={executable_status}"
        )


def _list_models(config: AppConfig) -> None:
    for model_id, model in config.models.items():
        print(f"{model_id}\t{model.role}\t{model.name}\t{model.model_path}")


def _runner_check(config: AppConfig) -> None:
    failed = False
    for result in run_preflight(config):
        status = "ok" if result.ok else ("missing" if result.required else "warn")
        print(f"{status}\t{result.name}\t{result.detail}")
        failed = failed or (result.required and not result.ok)
    if failed:
        raise SystemExit(1)


def _ops_status(config: AppConfig) -> None:
    state_dir = config.trace_dir / "state"
    monitor = HealthMonitor(
        task_store=TaskStore(default_state_db(config)),
        workflow_store=WorkflowStore(state_dir / "workflows.sqlite3"),
        source_store=SourceStore(state_dir / "sources.sqlite3"),
        artifact_store=ArtifactStore(state_dir / "artifacts.sqlite3"),
        approvals=ApprovalService(ApprovalStore(state_dir / "approvals.jsonl")),
    )
    print(json.dumps(monitor.snapshot().to_record(), ensure_ascii=False, indent=2, sort_keys=True))


def _ops_smoke(
    config: AppConfig,
    state_dir: str,
    include_model: bool,
    model_id: str,
    model_max_tokens: int,
    prompt: str,
) -> None:
    result = run_operational_smoke(
        config,
        state_dir=state_dir or None,
        include_model=include_model,
        model_id=model_id or None,
        model_max_tokens=model_max_tokens or None,
        model_prompt=prompt,
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _requirements_smoke(
    config: AppConfig,
    state_dir: str,
    experience_path: str,
    persist_experience: bool,
) -> None:
    result = run_requirement_smoke(
        config,
        state_dir=state_dir or config.trace_dir / "state" / "requirements_smoke",
        experience_path=experience_path or config.trace_dir / "experience.jsonl",
        persist_experience=persist_experience,
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _experience_list(config: AppConfig, experience_path: str, limit: int) -> None:
    store = ExperienceStore(experience_path or config.trace_dir / "experience.jsonl")
    print(
        json.dumps(
            [event.to_record() for event in store.list(limit=limit)],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _real_bench(config: AppConfig, args: argparse.Namespace) -> None:
    result = run_real_benchmark(
        config,
        RealBenchmarkOptions(
            state_dir=args.state_dir or config.trace_dir / "state" / "real_bench",
            experience_path=args.experience_path or config.trace_dir / "experience.jsonl",
            persist_experience=not args.no_persist_experience,
            include_network=not args.skip_network,
            include_ntfy=not args.skip_ntfy,
            include_model=not args.skip_model,
            model_id=args.model,
            model_max_tokens=args.model_max_tokens,
            model_prompt=args.prompt,
            reddit_url=args.reddit_url or RealBenchmarkOptions.reddit_url,
            dcinside_url=args.dcinside_url or RealBenchmarkOptions.dcinside_url,
            ticket_url=args.ticket_url,
        ),
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _finish_line_bench(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state" / "finish_line"
    result = run_frontdoor_finish_line_benchmark(
        config,
        state_dir=state_dir,
        request=args.request,
        answers=args.answer or DEFAULT_FINISH_LINE_ANSWERS,
        source_url=args.source_url,
        source_name=args.source_name,
        source_aliases=args.source_alias or DEFAULT_FINISH_LINE_ALIASES,
        ntfy_topic=args.ntfy_topic,
        ntfy_server=args.ntfy_server,
        web_url=args.web_url,
        timeout_s=args.timeout_s,
        require_delivery=not args.allow_no_delivery,
        synthesis_model_id=args.synthesis_model,
        synthesis_max_tokens=args.synthesis_max_tokens,
        require_model_synthesis=args.require_model_synthesis,
        preseed_source=not args.no_preseed_source,
        source_discovery_model_id=args.source_discovery_model,
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _web_collect(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state" / "web_collect"
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    source = source_store.add_source(
        SourceDefinition(
            kind=SourceKind.WEB_PAGE,
            name=args.name,
            locator=args.url,
            enabled=True,
            metadata={
                "extract": {
                    "href_contains": list(args.href_contains or []),
                    "href_contains_all": list(args.href_contains_all or []),
                    "href_excludes": list(args.href_excludes or []),
                    "text_excludes": list(args.text_excludes or []),
                    "text_exclude_regexes": list(args.text_exclude_regex or []),
                    "min_text_chars": args.min_text_chars,
                    "limit": args.limit,
                }
            },
        )
    )
    result = SourceRuntime(source_store=source_store, resource_store=resource_store).collect(source.source_id)
    resources = [resource_store.get(resource_id) for resource_id in result.resource_ids]
    print(
        json.dumps(
            {
                "ok": True,
                "state_dir": str(state_dir),
                "source_id": source.source_id,
                "collected_count": result.collected_count,
                "new_count": result.new_count,
                "quality": result.quality.to_record(),
                "resources": [
                    {
                        "resource_id": resource.resource_id,
                        "uri": resource.uri,
                        "title": resource.title,
                        "content_text": resource.content_text[:500],
                        "metadata": resource.metadata,
                    }
                    for resource in resources
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _sources(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    if args.action == "add-web":
        if not args.url:
            raise SystemExit("--url is required for sources add-web")
        source = source_store.add_source(
            SourceDefinition(
                kind=SourceKind.WEB_PAGE,
                name=args.name or args.url,
                locator=args.url,
                enabled=True,
                metadata={
                    "aliases": list(args.alias or []),
                    "extract": _extract_metadata(args),
                },
            )
        )
        payload = {"ok": True, "source": source.to_record()}
    elif args.action == "list":
        payload = {
            "ok": True,
            "sources": [
                source.to_record()
                for source in source_store.list_sources(limit=args.limit)
            ],
        }
    elif args.action == "collect":
        if not args.source_id:
            raise SystemExit("--source-id is required for sources collect")
        result = SourceRuntime(
            source_store=source_store,
            resource_store=resource_store,
        ).collect(args.source_id)
        payload = {
            "ok": True,
            "collection": {
                "source_id": result.source_id,
                "collected_count": result.collected_count,
                "new_count": result.new_count,
                "resource_ids": result.resource_ids,
                "recent_resource_ids": result.recent_resource_ids,
                "quality": result.quality.to_record(),
            },
        }
    else:
        raise ValueError(f"unsupported sources action: {args.action}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _source_discovery(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    task_store = TaskStore(state_dir / "agentic.sqlite3")
    spec = workflow_store.get_spec(args.workflow_id)
    missing_sources = _declared_source_labels(spec.to_record())
    if not missing_sources:
        raise SystemExit("workflow has no declared source labels to discover")
    task = SourceDiscoveryEnqueuer(
        task_store=task_store,
        state_dir=state_dir,
        config_path=str(config.config_path),
        model_id=args.model or config.runtime.default_subagent_model,
    ).enqueue(
        workflow_id=spec.workflow_id,
        user_request=_workflow_source_context(spec.to_record()),
        missing_sources=missing_sources,
        feedback=args.feedback,
    )
    workflow_store.append_event(
        "workflow_source_discovery_feedback_enqueued",
        {
            "task_id": task.task_id,
            "missing_sources": missing_sources,
            "feedback_chars": len(args.feedback.strip()),
        },
        workflow_id=spec.workflow_id,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "task": _task_record_payload(task),
                "workflow_id": spec.workflow_id,
                "missing_sources": missing_sources,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _task_record_payload(task: object) -> dict[str, object]:
    return {
        "task_id": getattr(task, "task_id", ""),
        "kind": getattr(task, "kind", ""),
        "status": getattr(getattr(task, "status", ""), "value", getattr(task, "status", "")),
        "input": getattr(task, "input", {}),
        "result": getattr(task, "result", None),
        "error": getattr(task, "error", None),
        "created_at": getattr(task, "created_at", ""),
        "updated_at": getattr(task, "updated_at", ""),
    }


def _declared_source_labels(spec: dict[str, object]) -> list[str]:
    labels: list[str] = []
    for source in spec.get("sources") or []:
        if not isinstance(source, dict):
            continue
        label = str(source.get("type") or source.get("name") or "").strip()
        if label:
            labels.append(label)
    return labels


def _workflow_source_context(spec: dict[str, object]) -> str:
    inputs = spec.get("inputs") if isinstance(spec.get("inputs"), dict) else {}
    slot_answers = inputs.get("slot_answers") if isinstance(inputs, dict) else {}
    parts = [
        f"description: {spec.get('description') or ''}",
        f"goal: {spec.get('goal') or ''}",
        f"sources: {spec.get('sources') or []}",
    ]
    if isinstance(slot_answers, dict):
        for key in sorted(slot_answers):
            parts.append(f"{key}: {slot_answers[key]}")
    return "\n".join(parts)


def _tooling(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    store = ToolingBacklogStore(state_dir / "tooling.sqlite3")
    payload = {
        "ok": True,
        "tooling": [
            request.to_record()
            for request in store.list(
                workflow_id=args.workflow_id or None,
                status=args.status or None,
                limit=args.limit,
            )
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _source_strategy(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    proposal_store = SourceStrategyProposalStore(state_dir / "source_strategy.sqlite3")
    service = SourceStrategyWorkshopService(
        source_store=SourceStore(state_dir / "sources.sqlite3"),
        proposal_store=proposal_store,
        tooling_store=ToolingBacklogStore(state_dir / "tooling.sqlite3"),
    )
    if args.action == "propose":
        if not args.tooling_id:
            raise SystemExit("--tooling-id is required for source-strategy propose")
        payload = {"ok": True, "proposal": service.propose_from_tooling(args.tooling_id).to_record()}
    elif args.action == "list":
        payload = {
            "ok": True,
            "proposals": [
                proposal.to_record()
                for proposal in proposal_store.list(
                    source_id=args.source_id or None,
                    status=args.status or None,
                    limit=args.limit,
                )
            ],
        }
    elif args.action == "inspect":
        if not args.proposal_id:
            raise SystemExit("--proposal-id is required for source-strategy inspect")
        payload = {"ok": True, "proposal": proposal_store.get(args.proposal_id).to_record()}
    elif args.action == "apply":
        if not args.proposal_id:
            raise SystemExit("--proposal-id is required for source-strategy apply")
        payload = {"ok": True, "proposal": service.apply(args.proposal_id).to_record()}
    elif args.action == "reject":
        if not args.proposal_id:
            raise SystemExit("--proposal-id is required for source-strategy reject")
        payload = {"ok": True, "proposal": service.reject(args.proposal_id).to_record()}
    elif args.action == "recover":
        if not args.tooling_id:
            raise SystemExit("--tooling-id is required for source-strategy recover")
        recovery = build_source_strategy_recovery_service(state_dir).recover_tooling(
            args.tooling_id,
            auto_apply=not args.no_auto_apply,
            rerun=not args.no_rerun,
        )
        payload = {"ok": recovery.ok, "recovery": recovery.to_record()}
    elif args.action == "recover-pending":
        recoveries = build_source_strategy_recovery_service(state_dir).recover_pending(
            limit=args.limit,
            auto_apply=not args.no_auto_apply,
            rerun=not args.no_rerun,
        )
        payload = {
            "ok": all(recovery.ok for recovery in recoveries),
            "recoveries": [recovery.to_record() for recovery in recoveries],
        }
    elif args.action == "recover-task":
        store = TaskStore(state_dir / "agentic.sqlite3")
        pool = TaskPool(
            store=store,
            executor=TaskRouter(
                {
                    SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                        default_state_dir=state_dir,
                    )
                }
            ),
            max_workers=1,
        )
        task = store.create_task(
            kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND,
            input={
                "state_dir": str(state_dir),
                "tooling_id": args.tooling_id,
                "limit": args.limit,
                "auto_apply": not args.no_auto_apply,
                "rerun": not args.no_rerun,
            },
        )
        try:
            if args.no_wait:
                payload = {"ok": True, "task": _task_to_record(store.get_task(task.task_id))}
            else:
                pool.kick()
                task_record = _wait_for_terminal_task(store, task.task_id, timeout_s=args.timeout_s)
                payload = {
                    "ok": task_record.status.value == "completed"
                    and bool((task_record.result or {}).get("ok", False)),
                    "task": _task_to_record(task_record),
                    "events": store.list_events(task.task_id),
                }
        finally:
            pool.shutdown(wait=not args.no_wait)
    elif args.action == "kick-recovery":
        store = TaskStore(state_dir / "agentic.sqlite3")
        pool = TaskPool(
            store=store,
            executor=TaskRouter(
                {
                    SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                        default_state_dir=state_dir,
                    )
                }
            ),
            max_workers=1,
        )
        submitted = pool.kick()
        try:
            if not args.no_wait:
                _wait_for_pool_idle(pool, timeout_s=args.timeout_s)
            tasks = store.list_tasks(kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND, limit=args.limit)
            payload = {
                "ok": all(task.status.value == "completed" for task in tasks if task.status.value != "queued"),
                "submitted": submitted,
                "tasks": [_task_to_record(task) for task in tasks],
            }
        finally:
            pool.shutdown(wait=not args.no_wait)
    else:
        raise ValueError(f"unsupported source strategy action: {args.action}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not payload["ok"]:
        raise SystemExit(1)


def _extract_metadata(args: argparse.Namespace) -> dict:
    return {
        "href_contains": list(args.href_contains or []),
        "href_contains_all": list(args.href_contains_all or []),
        "href_excludes": list(args.href_excludes or []),
        "text_excludes": list(args.text_excludes or []),
        "text_exclude_regexes": list(args.text_exclude_regex or []),
        "min_text_chars": args.min_text_chars,
        "limit": args.limit,
    }


def _resource_trends(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state" / "web_collect"
    store = ResourceStore(state_dir / "resources.sqlite3")
    summary = summarize_resource_trends(
        store,
        query=args.query,
        limit=args.limit,
        top_n=args.top_n,
    )
    print(json.dumps(summary.to_record(), ensure_ascii=False, indent=2, sort_keys=True))


def _skill_workshop(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    approvals = ApprovalService(ApprovalStore(state_dir / "approvals.jsonl"))
    service = SkillWorkshopService(
        SkillWorkshopStore(state_dir / "skill_workshop.sqlite3"),
        skills_root=args.skills_root,
    )
    if args.action == "create":
        body = args.proposal_body
        if args.proposal_file:
            body = Path(args.proposal_file).read_text(encoding="utf-8")
        proposal = service.propose_create(
            name=args.name,
            description=args.description,
            proposal_body=body,
            source="cli",
        )
        payload = {"ok": True, "proposal": proposal.to_record()}
    elif args.action == "list":
        proposals = service.list(status=args.status or None, limit=args.limit)
        payload = {"ok": True, "proposals": [proposal.to_record() for proposal in proposals]}
    elif args.action == "inspect":
        payload = {"ok": True, "proposal": service.inspect(args.proposal_id).to_record()}
    elif args.action == "review":
        payload = {"ok": True, "review": service.review(args.proposal_id).to_record()}
    elif args.action == "reject":
        payload = {"ok": True, "proposal": service.reject(args.proposal_id, reason=args.reason).to_record()}
    elif args.action == "quarantine":
        payload = {"ok": True, "proposal": service.quarantine(args.proposal_id, reason=args.reason).to_record()}
    elif args.action == "request-apply":
        approval = service.request_apply(
            args.proposal_id,
            approvals=approvals,
            reason=args.reason,
        )
        payload = {"ok": True, "approval": approval.to_record()}
    elif args.action == "apply":
        approval = approvals.get(args.approval_id)
        proposal = service.apply(
            args.proposal_id,
            approval=approval,
            reason=args.reason,
        )
        payload = {"ok": True, "proposal": proposal.to_record()}
    else:
        raise SystemExit(f"unsupported skill-workshop action: {args.action}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _approvals(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    service = ApprovalService(ApprovalStore(state_dir / "approvals.jsonl"))
    if args.action == "list":
        payload = {"ok": True, "approvals": [item.to_record() for item in service.store.list_all()]}
    elif args.action == "approve":
        payload = {"ok": True, "approval": service.approve(args.approval_id).to_record()}
    elif args.action == "deny":
        payload = {"ok": True, "approval": service.deny(args.approval_id).to_record()}
    else:
        raise SystemExit(f"unsupported approvals action: {args.action}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _harness_probe(config: AppConfig, args: argparse.Namespace) -> None:
    result = run_workflow_builder_probe(
        config,
        request=args.request,
        answers=args.answer or DEFAULT_PROBE_ANSWERS,
        state_dir=args.state_dir or None,
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _harness_probe_task(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    store = TaskStore(state_dir / "agentic.sqlite3")
    pool = TaskPool(
        store=store,
        executor=TaskRouter(
            {
                WORKFLOW_BUILDER_PROBE_TASK_KIND: WorkflowBuilderProbeExecutor(
                    config=config,
                    state_dir=state_dir,
                )
            }
        ),
        max_workers=1,
    )
    task = store.create_task(
        kind=WORKFLOW_BUILDER_PROBE_TASK_KIND,
        input={
            "request": args.request,
            "answers": args.answer or DEFAULT_PROBE_ANSWERS,
            "state_dir": str(state_dir),
        },
    )
    pool.kick()
    try:
        if args.no_wait:
            payload = {"ok": True, "task": _task_to_record(store.get_task(task.task_id))}
        else:
            payload = {
                "ok": True,
                "task": _task_to_record(
                    _wait_for_terminal_task(store, task.task_id, timeout_s=args.timeout_s)
                ),
                "events": store.list_events(task.task_id),
            }
            payload["ok"] = payload["task"]["status"] == "completed"
    finally:
        pool.shutdown(wait=not args.no_wait)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not payload["ok"]:
        raise SystemExit(1)


def _harness_workflow_spec_probe(config: AppConfig, args: argparse.Namespace) -> None:
    result = run_workflow_spec_probe(
        config,
        request=args.request,
        answers=args.answer or DEFAULT_PROBE_ANSWERS,
        state_dir=args.state_dir or None,
    )
    print(json.dumps(result.to_record(), ensure_ascii=False, indent=2, sort_keys=True))
    if not result.ok:
        raise SystemExit(1)


def _harness_workflow_spec_probe_task(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    store = TaskStore(state_dir / "agentic.sqlite3")
    pool = TaskPool(
        store=store,
        executor=TaskRouter(
            {
                WORKFLOW_SPEC_PROBE_TASK_KIND: WorkflowSpecProbeExecutor(
                    config=config,
                    state_dir=state_dir,
                )
            }
        ),
        max_workers=1,
    )
    task = store.create_task(
        kind=WORKFLOW_SPEC_PROBE_TASK_KIND,
        input={
            "request": args.request,
            "answers": args.answer or DEFAULT_PROBE_ANSWERS,
            "state_dir": str(state_dir),
        },
    )
    pool.kick()
    try:
        if args.no_wait:
            payload = {"ok": True, "task": _task_to_record(store.get_task(task.task_id))}
        else:
            payload = {
                "ok": True,
                "task": _task_to_record(
                    _wait_for_terminal_task(store, task.task_id, timeout_s=args.timeout_s)
                ),
                "events": store.list_events(task.task_id),
            }
            payload["ok"] = payload["task"]["status"] == "completed"
    finally:
        pool.shutdown(wait=not args.no_wait)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not payload["ok"]:
        raise SystemExit(1)


def _workflow_lifecycle(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    source_store = SourceStore(state_dir / "sources.sqlite3")
    service = WorkflowLifecycleService(
        workflow_store=workflow_store,
        source_store=source_store,
        schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
        artifact_store=ArtifactStore(state_dir / "artifacts.sqlite3"),
        resource_store=ResourceStore(state_dir / "resources.sqlite3"),
        tooling_store=ToolingBacklogStore(state_dir / "tooling.sqlite3"),
        source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
            task_store=TaskStore(state_dir / "agentic.sqlite3"),
            state_dir=state_dir,
        ),
        source_discovery_enqueuer=SourceDiscoveryEnqueuer(
            task_store=TaskStore(state_dir / "agentic.sqlite3"),
            state_dir=state_dir,
            config_path=str(config.config_path),
            model_id=config.runtime.default_subagent_model,
        ),
    )
    payload: dict[str, object]
    try:
        if args.action == "review":
            payload = {"ok": True, "review": service.review(args.workflow_id).to_record()}
        elif args.action == "bind-sources":
            result = service.bind_sources(args.workflow_id)
            payload = {"ok": result.ok, "source_binding": result.to_record()}
        elif args.action == "approve":
            payload = {"ok": True, "workflow": service.approve(args.workflow_id).to_record()}
        elif args.action == "activate":
            payload = {"ok": True, "workflow": service.activate(args.workflow_id).to_record()}
        elif args.action == "run":
            result = service.run_once(args.workflow_id)
            payload = {"ok": result.ok, "run": result.run.to_record()}
        elif args.action == "events":
            payload = {
                "ok": True,
                "events": workflow_store.list_events(
                    workflow_id=args.workflow_id,
                    limit=args.limit,
                ),
            }
        else:
            raise ValueError(f"unsupported workflow lifecycle action: {args.action}")
    except Exception as exc:
        payload = {
            "ok": False,
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
            "events": workflow_store.list_events(workflow_id=args.workflow_id, limit=args.limit),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not payload["ok"]:
        raise SystemExit(1)


def _scheduler_run_due(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    artifact_store = ArtifactStore(state_dir / "artifacts.sqlite3")
    runner = SchedulerRunner(
        schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
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
                tooling_store=ToolingBacklogStore(state_dir / "tooling.sqlite3"),
                source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                    task_store=TaskStore(state_dir / "agentic.sqlite3"),
                    state_dir=state_dir,
                ),
            )
        ),
    )
    results = runner.run_due_once(now=args.now or None)
    print(
        json.dumps(
            {
                "ok": all(result.ok for result in results),
                "runs": [
                    {
                        "schedule_id": result.schedule.schedule_id,
                        "workflow_id": result.schedule.workflow_id,
                        "workflow_run_id": result.workflow_run_id,
                        "ok": result.ok,
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _runtime_tick(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    task_store = TaskStore(state_dir / "agentic.sqlite3")
    recovered = recover_interrupted_tasks(task_store)
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    artifact_store = ArtifactStore(state_dir / "artifacts.sqlite3")
    tooling_store = ToolingBacklogStore(state_dir / "tooling.sqlite3")
    task_pool = TaskPool(
        store=task_store,
        executor=TaskRouter(
            {
                SOURCE_DISCOVERY_TASK_KIND: SourceDiscoveryExecutor(
                    config=config,
                    default_state_dir=state_dir,
                ),
                SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                    default_state_dir=state_dir,
                )
            }
        ),
        max_workers=1,
    )
    ntfy_channel = (
        NtfyChannel(
            NtfyConfig(
                enabled=True,
                server=args.ntfy_server,
                topic=args.ntfy_topic,
                title="Agentic report ready",
                web_url=args.web_url,
            )
        )
        if args.ntfy_enabled and args.ntfy_topic
        else None
    )
    scheduler = SchedulerRunner(
        schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
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
                tooling_store=tooling_store,
                source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                    task_store=task_store,
                    state_dir=state_dir,
                ),
            )
        ),
    )
    tick = RuntimeTickService(
        task_pool=task_pool,
        watchdog=Watchdog(task_store),
        scheduler=scheduler,
        report_delivery=ReportDeliveryService(
            artifact_store=artifact_store,
            delivery_store=DeliveryStore(state_dir / "deliveries.sqlite3"),
            ntfy_channel=ntfy_channel,
            web_url=args.web_url,
        ),
    )
    try:
        result = tick.run_once(
            wait=not args.no_wait,
            timeout_s=args.timeout_s,
        )
    finally:
        task_pool.shutdown(wait=not args.no_wait)
    print(
        json.dumps(
            {
                **result.to_record(),
                "recovered_interrupted_task_ids": recovered,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    if not result.ok:
        raise SystemExit(1)


def _runtime_daemon(config: AppConfig, args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir) if args.state_dir else config.trace_dir / "state"
    task_store = TaskStore(state_dir / "agentic.sqlite3")
    recovered = recover_interrupted_tasks(task_store)
    workflow_store = WorkflowStore(state_dir / "workflows.sqlite3")
    source_store = SourceStore(state_dir / "sources.sqlite3")
    resource_store = ResourceStore(state_dir / "resources.sqlite3")
    artifact_store = ArtifactStore(state_dir / "artifacts.sqlite3")
    tooling_store = ToolingBacklogStore(state_dir / "tooling.sqlite3")
    task_pool = TaskPool(
        store=task_store,
        executor=TaskRouter(
            {
                SOURCE_DISCOVERY_TASK_KIND: SourceDiscoveryExecutor(
                    config=config,
                    default_state_dir=state_dir,
                ),
                SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                    default_state_dir=state_dir,
                )
            }
        ),
        max_workers=1,
    )
    ntfy_channel = (
        NtfyChannel(
            NtfyConfig(
                enabled=True,
                server=args.ntfy_server,
                topic=args.ntfy_topic,
                title="Agentic report ready",
                web_url=args.web_url,
            )
        )
        if args.ntfy_enabled and args.ntfy_topic
        else None
    )
    workflow_builder = WorkflowBuilder(
        WorkflowInterpreter(
            workflow_store=workflow_store,
            artifact_store=artifact_store,
            source_runtime=SourceRuntime(
                source_store=source_store,
                resource_store=resource_store,
            ),
            resource_store=resource_store,
            tooling_store=tooling_store,
            source_recovery_enqueuer=SourceStrategyRecoveryEnqueuer(
                task_store=task_store,
                state_dir=state_dir,
            ),
        )
    )
    daemon = RuntimeDaemonLoop(
        tick_service=RuntimeTickService(
            task_pool=task_pool,
            watchdog=Watchdog(task_store),
            scheduler=SchedulerRunner(
                schedule_store=ScheduleStore(state_dir / "schedules.sqlite3"),
                workflow_store=workflow_store,
                builder=workflow_builder,
            ),
            report_delivery=ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=DeliveryStore(state_dir / "deliveries.sqlite3"),
                ntfy_channel=ntfy_channel,
                web_url=args.web_url,
            ),
        ),
        interval_s=args.interval_s,
        tick_timeout_s=args.timeout_s,
        wait_for_tasks=args.wait_for_tasks,
    )
    try:
        daemon.start()
        if args.duration_s > 0:
            time.sleep(args.duration_s)
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        daemon.stop()
        task_pool.shutdown(wait=False)
    print(
        json.dumps(
            {
                "ok": True,
                "recovered_interrupted_task_ids": recovered,
                "daemon": daemon.snapshot().to_record(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _wait_for_terminal_task(
    store: TaskStore,
    task_id: str,
    *,
    timeout_s: float,
):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        task = store.get_task(task_id)
        if task.status in TERMINAL_STATUSES:
            return task
        time.sleep(0.25)
    raise TimeoutError(f"task {task_id} did not finish within {timeout_s}s")


def _wait_for_pool_idle(pool: TaskPool, *, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if pool.running_count() == 0:
            return
        time.sleep(0.25)
    raise TimeoutError(f"task pool did not become idle within {timeout_s}s")


def _task_to_record(task) -> dict:
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


def _smoke(
    config: AppConfig,
    model_id: str,
    prompt: str,
    max_tokens: int,
) -> None:
    selected_id = model_id or config.runtime.default_master_model
    model = config.model(selected_id)
    if max_tokens > 0:
        model = replace(model, max_tokens=max_tokens)
    if not model.executable and not model.command_template:
        raise SystemExit(
            f"model '{selected_id}' has no executable configured. "
            "Set executable or command_template in config/config.toml."
        )

    builder = PromptBuilder.from_files(
        config.prompts.master,
        config.prompts.subagent,
        config.prompts.tool_call_grammar,
    )
    if model.role == "subagent":
        task = SubAgentTask(prompt)
        tool_schemas = ToolRegistry.with_defaults().schemas()
        full_prompt = (
            builder.subagent_user_prompt(task, tool_schemas)
            if model.system_prompt
            else builder.subagent_prompt(task, tool_schemas)
        )
    elif model.system_prompt:
        full_prompt = prompt
    else:
        full_prompt = builder.master_prompt(prompt)
    trace = TraceLogger(config.runtime.trace_file)
    response = LocalGGUFProvider(model).generate(full_prompt, trace=trace)
    print(response.text)


def _serve(config: AppConfig, args: argparse.Namespace) -> None:
    import uvicorn

    from agentic.app.channel_app import create_channel_app

    uvicorn.run(
        create_channel_app(
            config,
            daemon_interval_s=args.daemon_interval_s,
            daemon_tick_timeout_s=args.daemon_timeout_s,
            ntfy_enabled=args.ntfy_enabled,
            ntfy_topic=args.ntfy_topic,
            ntfy_server=args.ntfy_server,
            web_url=f"http://{args.host}:{args.port}",
        ),
        host=args.host,
        port=args.port,
    )


def _status(path: Path) -> str:
    return "ok" if path.exists() else "missing"


if __name__ == "__main__":
    main()
