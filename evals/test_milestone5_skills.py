from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.connectors import ConnectorRegistry
from agentic.agents.master import MasterAgent
from agentic.agents.subagent import SubAgent
from agentic.models.local_gguf import ModelResponse
from agentic.prompts.builder import PromptBuilder
from agentic.skills import SkillLoadError, SkillLoader, SkillRegistry, SkillRequirementError
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry


class Milestone5SkillTests(unittest.TestCase):
    def test_sample_skills_load(self) -> None:
        skills = SkillLoader("skills").load_all()

        self.assertIn("idea-capture", {skill.name for skill in skills})

    def test_invalid_frontmatter_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad" / "SKILL.md"
            path.parent.mkdir()
            path.write_text("no frontmatter", encoding="utf-8")

            with self.assertRaises(SkillLoadError):
                SkillLoader().load(path)

    def test_disabled_skill_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "off" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(
                "---\nname: off\ndescription: Off\nrequires:\n  connectors: []\n  tools: []\n  resources: []\ntriggers:\n  keywords: []\n  task_kinds: []\nenabled: false\n---\nbody",
                encoding="utf-8",
            )

            skills = SkillLoader(tmpdir).load_all()

        self.assertEqual(skills, [])

    def test_missing_connector_reports_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "needs" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(
                "---\nname: needs\ndescription: Needs connector\nrequires:\n  connectors: [gmail]\n  tools: []\n  resources: []\ntriggers:\n  keywords: [mail]\n  task_kinds: []\nenabled: true\n---\nbody",
                encoding="utf-8",
            )
            skill = SkillLoader().load(path)
            registry = SkillRegistry([skill], connectors=ConnectorRegistry([]))

            with self.assertRaises(SkillRequirementError):
                registry.check_requirements(skill)

    def test_routing_and_prompt_context(self) -> None:
        skills = SkillLoader("skills").load_all()
        registry = SkillRegistry(
            skills,
            connectors=ConnectorRegistry([]),
            tools=ToolRegistry.with_defaults(),
        )

        selected = registry.route("새 아이디어가 있어")
        context = registry.prompt_context(selected)

        self.assertIn("idea-capture", [skill.name for skill in selected])
        self.assertIn("Normalize the user's idea", context)

    def test_active_vague_workflow_builder_routes_korean_workflow_request(self) -> None:
        skills = SkillLoader("skills").load_all()
        registry = SkillRegistry(
            skills,
            connectors=ConnectorRegistry([]),
            tools=ToolRegistry.with_defaults(),
        )

        selected = registry.route("반복 자동화 워크플로우 만들어줘")
        context = registry.prompt_context(selected)

        self.assertIn("vague-workflow-builder", [skill.name for skill in selected])
        self.assertIn("Vague Workflow Builder", context)

    def test_master_agent_injects_selected_skill_context(self) -> None:
        provider = CapturingProvider(system_prompt=True)
        skills = SkillRegistry(
            SkillLoader("skills").load_all(),
            tools=ToolRegistry.with_defaults(),
        )
        agent = MasterAgent(
            provider=provider,  # type: ignore[arg-type]
            prompt_builder=PromptBuilder(),
            skills=skills,
        )

        agent.generate("반복 자동화 워크플로우 만들어줘")

        self.assertIn("Relevant skills:", provider.last_prompt)
        self.assertIn("vague-workflow-builder", provider.last_prompt)
        self.assertNotIn("gmail-newsletter-analysis", provider.last_prompt)

    def test_subagent_injects_selected_skill_context(self) -> None:
        provider = CapturingProvider(system_prompt=True)
        tools = ToolRegistry.with_defaults()
        skills = SkillRegistry(SkillLoader("skills").load_all(), tools=tools)
        agent = SubAgent(
            provider=provider,  # type: ignore[arg-type]
            prompt_builder=PromptBuilder(),
            tools=tools,
            skills=skills,
        )

        agent.generate_for_task(SubAgentTask("반복 자동화 워크플로우 proposal 만들어줘"))

        self.assertIn("Relevant skills:", provider.last_prompt)
        self.assertIn("vague-workflow-builder", provider.last_prompt)

    def test_skill_routing_uses_original_request_not_prompt_examples(self) -> None:
        provider = CapturingProvider(system_prompt=True)
        skills = SkillRegistry(
            SkillLoader("skills").load_all(),
            tools=ToolRegistry.with_defaults(),
        )
        agent = MasterAgent(
            provider=provider,  # type: ignore[arg-type]
            prompt_builder=PromptBuilder(),
            skills=skills,
        )
        message = (
            "Create a proposal.\n"
            "Original request: 반복 자동화 워크플로우 만들어줘\\n"
            "Question examples: Gmail, Obsidian, repo, browser, ticket."
        )

        selected = agent.selected_skill_names(message)

        self.assertIn("vague-workflow-builder", selected)
        self.assertNotIn("gmail-newsletter-analysis", selected)
        self.assertNotIn("obsidian-knowledge-linking", selected)


class CapturingProvider:
    def __init__(self, *, system_prompt: bool):
        self.config = type("Config", (), {"system_prompt": "sys" if system_prompt else ""})()
        self.last_prompt = ""

    def generate(self, prompt: str) -> ModelResponse:
        self.last_prompt = prompt
        return ModelResponse(text='{"action":"answer","answer":"ok"}', command=("fake",), returncode=0)


if __name__ == "__main__":
    unittest.main()
