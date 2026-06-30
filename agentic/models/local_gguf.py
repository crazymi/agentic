from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Mapping

from agentic.config.models import ModelConfig
from agentic.models.response_sanitizer import sanitize_model_output
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class ModelResponse:
    text: str
    command: tuple[str, ...]
    returncode: int
    stderr: str = ""
    raw_text: str = ""
    meta: Mapping[str, str] = field(default_factory=dict)


class LocalGGUFProvider:
    """Single local provider for configured GGUF command execution."""

    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(self, prompt: str, trace: TraceLogger | None = None) -> ModelResponse:
        command = self._build_command(prompt)
        if trace:
            trace.record(
                "model_call_started",
                {
                    "model_id": self.config.model_id,
                    "role": self.config.role,
                    "model_path": self.config.model_path,
                },
            )
        completed = subprocess.run(
            command,
            input=prompt if self.config.prompt_via_stdin else None,
            text=True,
            capture_output=True,
            timeout=self.config.timeout_s,
            check=False,
        )
        if completed.returncode != 0:
            if trace:
                trace.record(
                    "model_call_failed",
                    {
                        "model_id": self.config.model_id,
                        "returncode": completed.returncode,
                        "stderr": completed.stderr.strip(),
                    },
                )
            raise RuntimeError(
                f"local GGUF command failed for {self.config.role}: "
                f"returncode={completed.returncode} stderr={completed.stderr.strip()}"
            )
        response = ModelResponse(
            text=sanitize_model_output(completed.stdout),
            command=tuple(command),
            returncode=completed.returncode,
            stderr=completed.stderr.strip(),
            raw_text=completed.stdout.strip(),
            meta={
                "model_id": self.config.model_id,
                "role": self.config.role,
                "model": self.config.name,
            },
        )
        if trace:
            trace.record(
                "model_call_completed",
                {
                    "model_id": self.config.model_id,
                    "role": self.config.role,
                    "text_chars": len(response.text),
                },
            )
        return response

    def _build_command(self, prompt: str) -> list[str]:
        if self.config.command_template:
            return [
                part.format(
                    model_path=self.config.model_path,
                    prompt=prompt,
                    max_tokens=self.config.max_tokens,
                )
                for part in self.config.command_template
            ]

        if not self.config.executable:
            raise ValueError("LocalGGUFProvider requires an executable or command_template")

        command = [self.config.executable]
        command.extend(self.config.args)
        if self.config.model_path:
            command.extend(["-m", self.config.model_path])
        command.extend(["-n", str(self.config.max_tokens)])
        if self.config.system_prompt:
            command.extend(["-sys", self.config.system_prompt])
        if not self.config.prompt_via_stdin:
            command.extend(["-p", prompt])
        return command
