from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentic.config.settings import AppConfig


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def run_preflight(config: AppConfig) -> list[CheckResult]:
    results = [
        _command_check("git", ["git", "--version"]),
        _command_check("g++", ["g++", "--version"]),
        _cmake_check(config),
        _command_check("nvidia-smi", ["nvidia-smi"], required=False),
    ]
    for model_id, model in config.models.items():
        results.append(
            CheckResult(
                name=f"model_path:{model_id}",
                ok=Path(model.model_path).exists(),
                detail=model.model_path,
            )
        )
        executable_ok = bool(model.executable) and Path(model.executable).exists()
        results.append(
            CheckResult(
                name=f"executable:{model_id}",
                ok=executable_ok,
                detail=model.executable or "not configured",
            )
        )
    return results


def _command_check(name: str, command: list[str], required: bool = True) -> CheckResult:
    if shutil.which(command[0]) is None:
        return CheckResult(
            name=name,
            ok=False,
            detail="not found on PATH",
            required=required,
        )
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    output = (completed.stdout or completed.stderr).strip().splitlines()
    detail = output[0] if output else f"returncode={completed.returncode}"
    return CheckResult(
        name=name,
        ok=completed.returncode == 0,
        detail=detail,
        required=required,
    )


def _cmake_check(config: AppConfig) -> CheckResult:
    venv_cmake = config.venv / "bin" / "cmake"
    if venv_cmake.exists():
        return _command_check("cmake", [str(venv_cmake), "--version"])
    return _command_check("cmake", ["cmake", "--version"])
