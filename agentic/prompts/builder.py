from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic.tasks.subagent_task import SubAgentTask


MASTER_SYSTEM = """You are the master agent for a personal local harness.
Decide whether to answer directly or delegate a focused task to the subagent.
Keep decisions small, explicit, and traceable."""

SUBAGENT_SYSTEM = """You are a subagent in a personal local harness.
Use exactly one tool call when a tool is needed. Tool calls must be strict JSON:
{"tool": "name", "arguments": {"key": "value"}}"""


@dataclass(frozen=True)
class PromptBuilder:
    master_system: str = MASTER_SYSTEM
    subagent_system: str = SUBAGENT_SYSTEM
    tool_call_grammar: str = ""

    @classmethod
    def from_files(
        cls,
        master_path: str | Path,
        subagent_path: str | Path,
        tool_call_grammar_path: str | Path,
    ) -> "PromptBuilder":
        return cls(
            master_system=Path(master_path).read_text(encoding="utf-8").strip(),
            subagent_system=Path(subagent_path).read_text(encoding="utf-8").strip(),
            tool_call_grammar=Path(tool_call_grammar_path).read_text(encoding="utf-8").strip(),
        )

    def master_prompt(self, user_message: str) -> str:
        return "\n".join(
            [
                "<system>",
                self.master_system,
                "</system>",
                "<user>",
                user_message,
                "</user>",
            ]
        )

    def subagent_prompt(self, task: SubAgentTask, tool_schemas: list[dict[str, Any]]) -> str:
        return "\n".join(
            [
                "<system>",
                self.subagent_system,
                self.tool_call_grammar,
                "</system>",
                "<tools>",
                json.dumps(tool_schemas, ensure_ascii=False, sort_keys=True),
                "</tools>",
                "<task>",
                task.instruction,
                "</task>",
            ]
        )

    def subagent_user_prompt(self, task: SubAgentTask, tool_schemas: list[dict[str, Any]]) -> str:
        return "\n".join(
            [
                "Available tools:",
                json.dumps(tool_schemas, ensure_ascii=False, sort_keys=True),
                "",
                "Task:",
                task.instruction,
            ]
        )
