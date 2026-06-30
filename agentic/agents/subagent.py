from __future__ import annotations

from dataclasses import dataclass

from agentic.models.local_gguf import LocalGGUFProvider, ModelResponse
from agentic.prompts.builder import PromptBuilder
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry


@dataclass(frozen=True)
class SubAgent:
    provider: LocalGGUFProvider
    prompt_builder: PromptBuilder
    tools: ToolRegistry

    def generate_for_task(self, task: SubAgentTask) -> ModelResponse:
        prompt = (
            self.prompt_builder.subagent_user_prompt(task, self.tools.schemas())
            if self.provider.config.system_prompt
            else self.prompt_builder.subagent_prompt(task, self.tools.schemas())
        )
        return self.provider.generate(prompt)
