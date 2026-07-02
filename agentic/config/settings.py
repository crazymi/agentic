from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic.config.models import ModelConfig


@dataclass(frozen=True)
class PromptConfig:
    master: Path
    subagent: Path
    tool_call_grammar: Path


@dataclass(frozen=True)
class RuntimeConfig:
    default_master_model: str
    default_subagent_model: str
    trace_file: Path


@dataclass(frozen=True)
class AppConfig:
    root: Path
    config_path: Path
    package_manager: str
    venv: Path
    prompt_dir: Path
    model_dir: Path
    trace_dir: Path
    prompts: PromptConfig
    runtime: RuntimeConfig
    models: dict[str, ModelConfig]

    def model(self, model_id: str) -> ModelConfig:
        try:
            return self.models[model_id]
        except KeyError as exc:
            known = ", ".join(sorted(self.models))
            raise KeyError(f"unknown model id '{model_id}'. Known models: {known}") from exc


def load_app_config(config_path: str | Path = "config/config.toml") -> AppConfig:
    config_path = Path(config_path).resolve()
    root = config_path.parent.parent
    load_dotenv(root / ".env")
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    project = data.get("project", {})
    paths = data.get("paths", {})
    prompts = data.get("prompts", {})
    runtime = data.get("runtime", {})
    models = data.get("models", {})

    return AppConfig(
        root=root,
        config_path=config_path,
        package_manager=str(project.get("package_manager", "uv")),
        venv=_resolve(root, project.get("venv", ".venv")),
        prompt_dir=_resolve(root, paths.get("prompt_dir", "prompts")),
        model_dir=_resolve(root, paths.get("model_dir", "models")),
        trace_dir=_resolve(root, paths.get("trace_dir", "traces")),
        prompts=PromptConfig(
            master=_resolve(root, prompts.get("master", "prompts/master.md")),
            subagent=_resolve(root, prompts.get("subagent", "prompts/subagent.md")),
            tool_call_grammar=_resolve(
                root,
                prompts.get("tool_call_grammar", "prompts/tool_call_grammar.md"),
            ),
        ),
        runtime=RuntimeConfig(
            default_master_model=str(runtime.get("default_master_model", "")),
            default_subagent_model=str(runtime.get("default_subagent_model", "")),
            trace_file=_resolve(root, runtime.get("trace_file", "traces/phase0.jsonl")),
        ),
        models={
            model_id: _model_config_from_toml(model_id, raw, root)
            for model_id, raw in models.items()
        },
    )


def _model_config_from_toml(
    model_id: str,
    raw: dict[str, Any],
    root: Path,
) -> ModelConfig:
    return ModelConfig(
        model_id=model_id,
        name=str(raw.get("name", model_id)),
        role=str(raw["role"]),
        model_path=str(_resolve(root, raw.get("model_path", ""))) if raw.get("model_path") else "",
        executable=str(_resolve(root, raw.get("executable", ""))) if raw.get("executable") else "",
        args=tuple(str(arg) for arg in raw.get("args", [])),
        command_template=tuple(str(arg) for arg in raw.get("command_template", [])),
        system_prompt=_read_optional_text(root, raw.get("system_prompt_file", ""))
        or str(raw.get("system_prompt", "")),
        prompt_via_stdin=bool(raw.get("prompt_via_stdin", True)),
        timeout_s=float(raw.get("timeout_s", 120.0)),
        max_tokens=int(raw.get("max_tokens", 512)),
    )


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _read_optional_text(root: Path, value: str | Path) -> str:
    if not value:
        return ""
    return _resolve(root, value).read_text(encoding="utf-8").strip()


def load_dotenv(path: str | Path, *, override: bool = False) -> dict[str, str]:
    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return {}
    loaded: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_dotenv_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if not override and key in os.environ:
            continue
        os.environ[key] = value
        loaded[key] = value
    return loaded


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
        return None
    return key, _parse_dotenv_value(value.strip())


def _parse_dotenv_value(value: str) -> str:
    if not value:
        return ""
    if value[0] == value[-1:] and value[0] in {"'", '"'}:
        inner = value[1:-1]
        if value[0] == '"':
            return bytes(inner, "utf-8").decode("unicode_escape")
        return inner
    result: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "#":
            break
        result.append(char)
    return "".join(result).strip()
