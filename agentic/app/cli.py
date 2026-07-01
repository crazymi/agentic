from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.artifacts import ArtifactStore
from agentic.benchmarks import RealBenchmarkOptions, run_real_benchmark
from agentic.config.settings import AppConfig, load_app_config
from agentic.experience import ExperienceStore, run_requirement_smoke
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.ops import HealthMonitor, run_operational_smoke
from agentic.prompts.builder import PromptBuilder
from agentic.app.chat import run_chat_once, run_chat_repl
from agentic.runtime.preflight import run_preflight
from agentic.runtime.daemon import default_state_db
from agentic.sources import SourceStore
from agentic.tasks.store import TaskStore
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel import WorkflowStore


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
    real_bench.add_argument("--model-max-tokens", type=int, default=16, help="max tokens for model probe")
    real_bench.add_argument("--prompt", default="한국의 수도는 어디야? 답변만 한 문장으로 말해.", help="model prompt")
    real_bench.add_argument("--reddit-url", default="", help="Reddit JSON URL to crawl")
    real_bench.add_argument("--dcinside-url", default="", help="DCInside gallery URL to crawl")
    real_bench.add_argument("--ticket-url", default="", help="official ticket URL for live browser transaction probe")

    ask = subparsers.add_parser("ask", help="run one full-loop agent turn")
    ask.add_argument("message", nargs="+", help="message to send to the full-loop runtime")

    subparsers.add_parser("chat", help="start a simple full-loop chat REPL")

    serve = subparsers.add_parser("serve", help="start the local web channel")
    serve.add_argument("--host", default="127.0.0.1", help="bind host")
    serve.add_argument("--port", type=int, default=8765, help="bind port")

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
    if args.command == "ask":
        print(run_chat_once(config, " ".join(args.message)))
        return
    if args.command == "chat":
        run_chat_repl(config)
        return
    if args.command == "serve":
        _serve(config, args.host, args.port)
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


def _serve(config: AppConfig, host: str, port: int) -> None:
    import uvicorn

    from agentic.app.channel_app import create_channel_app

    uvicorn.run(create_channel_app(config), host=host, port=port)


def _status(path: Path) -> str:
    return "ok" if path.exists() else "missing"


if __name__ == "__main__":
    main()
