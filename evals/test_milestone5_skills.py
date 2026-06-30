from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.connectors import ConnectorRegistry, FakeConnector
from agentic.skills import SkillLoadError, SkillLoader, SkillRegistry, SkillRequirementError
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
            registry = SkillRegistry([skill], connectors=ConnectorRegistry([FakeConnector()]))

            with self.assertRaises(SkillRequirementError):
                registry.check_requirements(skill)

    def test_routing_and_prompt_context(self) -> None:
        skills = SkillLoader("skills").load_all()
        registry = SkillRegistry(
            skills,
            connectors=ConnectorRegistry([FakeConnector()]),
            tools=ToolRegistry.with_defaults(),
        )

        selected = registry.route("새 아이디어가 있어")
        context = registry.prompt_context(selected)

        self.assertIn("idea-capture", [skill.name for skill in selected])
        self.assertIn("Normalize the user's idea", context)


if __name__ == "__main__":
    unittest.main()
