from __future__ import annotations

from dataclasses import dataclass

from agentic.models.local_gguf import LocalGGUFProvider, ModelResponse
from agentic.prompts.builder import PromptBuilder


@dataclass(frozen=True)
class MasterAgent:
    provider: LocalGGUFProvider
    prompt_builder: PromptBuilder

    def generate(self, user_message: str) -> ModelResponse:
        prompt = (
            user_message
            if self.provider.config.system_prompt
            else self.prompt_builder.master_prompt(user_message)
        )
        return self.provider.generate(prompt)
