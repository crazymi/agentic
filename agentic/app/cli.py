from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from agentic.config.models import ModelConfig
from agentic.config.settings import AppConfig, load_app_config
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.app.chat import run_chat_once, run_chat_repl
from agentic.runtime.preflight import run_preflight
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal local GGUF agent harness")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--config", default="config/config.toml", help="path to config.toml")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("config-check", help="validate config, prompts, and model paths")
    subparsers.add_parser("list-models", help="list configured local models")
    subparsers.add_parser("runner-check", help="check local runner build/runtime prerequisites")

    ask = subparsers.add_parser("ask", help="run one full-loop agent turn")
    ask.add_argument("message", nargs="+", help="message to send to the full-loop runtime")

    subparsers.add_parser("chat", help="start a simple full-loop chat REPL")

    serve = subparsers.add_parser("serve", help="start the local web channel")
    serve.add_argument("--host", default="127.0.0.1", help="bind host")
    serve.add_argument("--port", type=int, default=8765, help="bind port")

    smoke = subparsers.add_parser("smoke", help="run one model smoke call")
    smoke.add_argument("--model", default="", help="configured model id")
    smoke.add_argument("--prompt", default="hello from phase 0", help="prompt text")
    smoke.add_argument("--fake", action="store_true", help="use fake provider command")
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
        _smoke(config, args.model, args.prompt, args.fake, args.max_tokens)
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
        executable_status = "fake-ready" if not model.executable else _status(Path(model.executable))
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


def _smoke(
    config: AppConfig,
    model_id: str,
    prompt: str,
    fake: bool,
    max_tokens: int,
) -> None:
    selected_id = model_id or config.runtime.default_master_model
    configured_model = config.model(selected_id)
    model = ModelConfig.fake(configured_model.role) if fake else configured_model
    if max_tokens > 0:
        model = replace(model, max_tokens=max_tokens)
    if not fake and not model.executable and not model.command_template:
        raise SystemExit(
            f"model '{selected_id}' has no executable configured. "
            "Use --fake or set executable in config/config.toml."
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
