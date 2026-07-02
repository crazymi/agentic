from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic.tools.base import ToolSpec


DEFAULT_TIMEOUT_S = 30.0
MAX_OUTPUT_CHARS = 32_000


@dataclass
class ProcessRecord:
    process: subprocess.Popen[str]
    command: str
    workdir: str
    started_at: float = field(default_factory=time.time)
    stdout: str = ""
    stderr: str = ""


_PROCESSES: dict[str, ProcessRecord] = {}


def exec_command(
    command: str,
    *,
    workdir: str = ".",
    timeout_s: float = DEFAULT_TIMEOUT_S,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    cwd = _resolve_workdir(workdir)
    completed = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        input=None,
        text=True,
        capture_output=True,
        timeout=max(0.1, float(timeout_s or DEFAULT_TIMEOUT_S)),
        env=_merged_env(env),
    )
    return {
        "command": command,
        "workdir": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": completed.stderr[-MAX_OUTPUT_CHARS:],
        "ok": completed.returncode == 0,
    }


def process(
    action: str,
    *,
    command: str = "",
    process_id: str = "",
    workdir: str = ".",
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if action == "start":
        if not command:
            raise ValueError("process start requires command")
        cwd = _resolve_workdir(workdir)
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_merged_env(env),
        )
        pid = f"proc_{uuid.uuid4().hex}"
        _PROCESSES[pid] = ProcessRecord(process=proc, command=command, workdir=str(cwd))
        return {"process_id": pid, "pid": proc.pid, "status": "running"}
    if action == "list":
        return {"processes": [_describe_process(pid, record) for pid, record in _PROCESSES.items()]}
    if action == "poll":
        record = _require_process(process_id)
        return _poll_process(process_id, record)
    if action == "kill":
        record = _require_process(process_id)
        record.process.terminate()
        return _poll_process(process_id, record)
    raise ValueError(f"unsupported process action: {action}")


def python_execute(
    code: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    workdir: str = ".",
) -> dict[str, Any]:
    cwd = _resolve_workdir(workdir)
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=max(0.1, float(timeout_s or DEFAULT_TIMEOUT_S)),
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": completed.stderr[-MAX_OUTPUT_CHARS:],
        "ok": completed.returncode == 0,
    }


def _require_process(process_id: str) -> ProcessRecord:
    if process_id not in _PROCESSES:
        raise KeyError(f"unknown process_id: {process_id}")
    return _PROCESSES[process_id]


def _poll_process(process_id: str, record: ProcessRecord) -> dict[str, Any]:
    proc = record.process
    status = "running" if proc.poll() is None else "exited"
    if status == "exited":
        stdout, stderr = proc.communicate(timeout=0.1)
        record.stdout += stdout
        record.stderr += stderr
    return {
        **_describe_process(process_id, record),
        "stdout": record.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": record.stderr[-MAX_OUTPUT_CHARS:],
    }


def _describe_process(process_id: str, record: ProcessRecord) -> dict[str, Any]:
    proc = record.process
    return {
        "process_id": process_id,
        "pid": proc.pid,
        "command": record.command,
        "workdir": record.workdir,
        "status": "running" if proc.poll() is None else "exited",
        "exit_code": proc.poll(),
        "started_at": record.started_at,
    }


def _resolve_workdir(workdir: str) -> Path:
    path = Path(workdir or ".")
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _merged_env(env: dict[str, str] | None) -> dict[str, str]:
    merged = dict(os.environ)
    for key, value in (env or {}).items():
        if key == "PATH" or key.startswith(("LD_", "DYLD_")):
            raise ValueError(f"unsafe env override is not allowed: {key}")
        merged[str(key)] = str(value)
    return merged


EXEC_TOOL = ToolSpec(
    name="exec",
    description="Run a shell command in the workspace and return exit code, stdout, and stderr.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "workdir": {"type": "string"},
            "timeout_s": {"type": "number"},
            "env": {"type": "object"},
        },
        "required": ["command"],
    },
    fn=exec_command,
)

PROCESS_TOOL = ToolSpec(
    name="process",
    description="Start, list, poll, or kill background shell processes for the current Python runtime.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["start", "list", "poll", "kill"]},
            "command": {"type": "string"},
            "process_id": {"type": "string"},
            "workdir": {"type": "string"},
            "env": {"type": "object"},
        },
        "required": ["action"],
    },
    fn=process,
)

PYTHON_EXECUTE_TOOL = ToolSpec(
    name="python_execute",
    description="Run short Python code with the current interpreter and return stdout/stderr.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout_s": {"type": "number"},
            "workdir": {"type": "string"},
        },
        "required": ["code"],
    },
    fn=python_execute,
)
