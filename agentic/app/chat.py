from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from agentic.config.settings import AppConfig


class ChatRuntime(Protocol):
    def run(self, message: str) -> Any:
        ...


RuntimeFactory = Callable[[AppConfig], ChatRuntime]


def run_chat_once(
    config: AppConfig,
    message: str,
    *,
    runtime: ChatRuntime | None = None,
    runtime_factory: RuntimeFactory | None = None,
) -> str:
    """Run one chat turn and return the final answer text."""
    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("message must not be empty")

    selected_runtime = runtime or _build_runtime(config, runtime_factory)
    result = selected_runtime.run(cleaned_message)
    return _answer_text(result)


def run_chat_repl(
    config: AppConfig,
    *,
    runtime_factory: RuntimeFactory | None = None,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], object] = print,
    prompt: str = "agentic> ",
) -> None:
    """Small REPL helper for future CLI integration."""
    runtime = _build_runtime(config, runtime_factory)
    while True:
        try:
            message = input_func(prompt)
        except EOFError:
            break

        if message.strip().lower() in {"", "exit", "quit"}:
            break
        output_func(run_chat_once(config, message, runtime=runtime))


def _build_runtime(
    config: AppConfig,
    runtime_factory: RuntimeFactory | None,
) -> ChatRuntime:
    if runtime_factory is not None:
        return runtime_factory(config)

    try:
        from agentic.runtime.full_loop import FullLoopRuntime  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FullLoopRuntime is not available yet. Pass a runtime or runtime_factory "
            "until Phase 1 integration wires the full loop."
        ) from exc

    from_config = getattr(FullLoopRuntime, "from_config", None)
    if callable(from_config):
        return from_config(config)
    return FullLoopRuntime(config)


def _answer_text(result: Any) -> str:
    if isinstance(result, str):
        return result

    for attr in ("final_answer", "answer", "text", "report"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value

    raise TypeError(
        "chat runtime result must be a string or expose final_answer, answer, text, or report"
    )
