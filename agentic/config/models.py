from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    name: str
    role: str
    model_path: str = ""
    executable: str = ""
    args: tuple[str, ...] = field(default_factory=tuple)
    command_template: tuple[str, ...] = field(default_factory=tuple)
    system_prompt: str = ""
    prompt_via_stdin: bool = True
    timeout_s: float = 120.0
    max_tokens: int = 512

    @classmethod
    def fake(cls, role: str) -> "ModelConfig":
        script = (
            "import sys; "
            "prompt=sys.stdin.read(); "
            "print(sys.argv[1] + ' response: ' + prompt[:10000])"
        )
        return cls(
            model_id=f"fake-{role}",
            name=f"fake-{role}",
            role=role,
            executable=sys.executable,
            command_template=(sys.executable, "-c", script, role),
            prompt_via_stdin=True,
            timeout_s=10.0,
        )


def model_config_from_env(role: str) -> ModelConfig:
    prefix = f"AGENTIC_{role.upper()}"
    model_path = os.getenv(f"{prefix}_MODEL_PATH", "")
    executable = os.getenv(f"{prefix}_EXECUTABLE", "")
    args = tuple(os.getenv(f"{prefix}_ARGS", "").split()) if os.getenv(f"{prefix}_ARGS") else ()

    if not executable:
        return ModelConfig.fake(role)

    return ModelConfig(
        model_id=role,
        name=os.getenv(f"{prefix}_MODEL_NAME", role),
        role=role,
        model_path=model_path,
        executable=executable,
        args=args,
        prompt_via_stdin=os.getenv(f"{prefix}_PROMPT_STDIN", "1") != "0",
        timeout_s=float(os.getenv(f"{prefix}_TIMEOUT_S", "120")),
        max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", "512")),
    )
