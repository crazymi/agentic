from __future__ import annotations

import re
from dataclasses import dataclass

from agentic.models.local_gguf import LocalGGUFProvider, ModelResponse
from agentic.prompts.builder import PromptBuilder
from agentic.skills.registry import SkillRegistry
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class SubAgent:
    provider: LocalGGUFProvider
    prompt_builder: PromptBuilder
    tools: ToolRegistry
    skills: SkillRegistry | None = None

    def generate_for_task(
        self,
        task: SubAgentTask,
        *,
        trace: TraceLogger | None = None,
    ) -> ModelResponse:
        tool_schemas = self._tool_schemas_for_task(task)
        skill_context = self.skill_context(task)
        provider = self._provider_for_task(task)
        prompt = (
            self.prompt_builder.subagent_user_prompt(
                task,
                tool_schemas,
                skill_context=skill_context,
            )
            if provider.config.system_prompt
            else self.prompt_builder.subagent_prompt(
                task,
                tool_schemas,
                skill_context=skill_context,
            )
        )
        try:
            return provider.generate(prompt, trace=trace)
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            return provider.generate(prompt)

    def _provider_for_task(self, task: SubAgentTask) -> LocalGGUFProvider:
        if _looks_like_skill_workshop_task(task.instruction) and self.provider.config.max_tokens > 384:
            return self.provider.with_max_tokens(384)
        if _looks_like_workflow_spec_task(task.instruction) and self.provider.config.max_tokens > 384:
            return self.provider.with_max_tokens(384)
        return self.provider

    def selected_skill_names(self, task: SubAgentTask) -> list[str]:
        if self.skills is None:
            return []
        return [skill.name for skill in self.skills.route(_skill_routing_text(task.instruction))]

    def skill_context(self, task: SubAgentTask) -> str:
        if self.skills is None:
            return ""
        selected = self.skills.route(_skill_routing_text(task.instruction))
        if not selected:
            return ""
        return self.skills.prompt_context(selected, max_body_chars=420)

    def _tool_schemas_for_task(self, task: SubAgentTask) -> list[dict]:
        instruction = task.instruction.lower()
        if "skill_workshop" in instruction or "skill proposal" in instruction or "스킬" in instruction:
            return self.tools.schema_names(["skill_workshop"])
        if "workflow_spec" in instruction or "workflow spec" in instruction or "workflowspec" in instruction:
            return self.tools.schema_names(["workflow_spec"])
        if "add tool" in instruction or "+" in instruction:
            return self.tools.schema_names(["add"])
        return self.tools.schemas()


def _skill_routing_text(text: str) -> str:
    match = re.search(r"Original request:\s*(.+)", text)
    if match:
        return match.group(1).split("\\n", 1)[0].strip()
    return text


def _looks_like_skill_workshop_task(text: str) -> bool:
    lowered = text.lower()
    return "skill_workshop" in lowered or "skill proposal" in lowered or "스킬" in lowered


def _looks_like_workflow_spec_task(text: str) -> bool:
    lowered = text.lower()
    return "workflow_spec" in lowered or "workflow spec" in lowered or "workflowspec" in lowered
