from __future__ import annotations

from agentic.connectors.registry import ConnectorRegistry
from agentic.skills.models import SkillPackage
from agentic.tools.registry import ToolRegistry


class SkillRequirementError(RuntimeError):
    pass


class SkillRegistry:
    def __init__(
        self,
        skills: list[SkillPackage],
        *,
        connectors: ConnectorRegistry | None = None,
        tools: ToolRegistry | None = None,
    ):
        self.skills = {skill.name: skill for skill in skills}
        self.connectors = connectors
        self.tools = tools

    def get(self, name: str) -> SkillPackage:
        return self.skills[name]

    def check_requirements(self, skill: SkillPackage) -> None:
        if self.connectors is not None:
            known = set(self.connectors.list_connectors())
            missing = [item for item in skill.manifest.requires.connectors if item not in known]
            if missing:
                raise SkillRequirementError(f"missing connectors: {', '.join(missing)}")
        if self.tools is not None:
            known_tools = {schema["name"] for schema in self.tools.schemas()}
            missing = [item for item in skill.manifest.requires.tools if item not in known_tools]
            if missing:
                raise SkillRequirementError(f"missing tools: {', '.join(missing)}")

    def route(self, text: str, *, task_kind: str = "") -> list[SkillPackage]:
        lowered = text.lower()
        selected: list[SkillPackage] = []
        for skill in self.skills.values():
            triggers = skill.manifest.triggers
            if task_kind and task_kind in triggers.task_kinds:
                selected.append(skill)
                continue
            if any(keyword.lower() in lowered for keyword in triggers.keywords):
                selected.append(skill)
        return selected

    def prompt_context(self, skills: list[SkillPackage]) -> str:
        blocks = []
        for skill in skills:
            self.check_requirements(skill)
            blocks.append(
                f"## Skill: {skill.name}\n"
                f"{skill.manifest.description}\n\n"
                f"{skill.body}"
            )
        return "\n\n".join(blocks)
