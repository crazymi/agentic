from __future__ import annotations

import re
from dataclasses import dataclass

from agentic.models.local_gguf import LocalGGUFProvider, ModelResponse
from agentic.prompts.builder import PromptBuilder
from agentic.skills.registry import SkillRegistry
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class MasterAgent:
    provider: LocalGGUFProvider
    prompt_builder: PromptBuilder
    skills: SkillRegistry | None = None

    def generate(
        self,
        user_message: str,
        *,
        trace: TraceLogger | None = None,
    ) -> ModelResponse:
        skill_context = self.skill_context(user_message)
        prompt_message = _with_inline_skill_context(user_message, skill_context)
        prompt = (
            prompt_message
            if self.provider.config.system_prompt
            else self.prompt_builder.master_prompt(user_message, skill_context=skill_context)
        )
        try:
            return self.provider.generate(prompt, trace=trace)
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            return self.provider.generate(prompt)

    def selected_skill_names(self, user_message: str) -> list[str]:
        if self.skills is None:
            return []
        return [skill.name for skill in self.skills.route(_skill_routing_text(user_message))]

    def skill_context(self, user_message: str) -> str:
        if self.skills is None:
            return ""
        selected = self.skills.route(_skill_routing_text(user_message))
        if not selected:
            return ""
        return self.skills.prompt_context(selected, max_body_chars=420)


def _with_inline_skill_context(user_message: str, skill_context: str) -> str:
    if not skill_context:
        return user_message
    return "\n".join(
        [
            "Relevant skills:",
            skill_context,
            "",
            "User message:",
            user_message,
        ]
    )


def _skill_routing_text(text: str) -> str:
    match = re.search(r"Original request:\s*(.+)", text)
    if match:
        return match.group(1).split("\\n", 1)[0].strip()
    return text
