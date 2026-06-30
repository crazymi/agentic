from __future__ import annotations

import unittest
from pathlib import Path

from agentic.skills import SkillLoader


class McpSkillCatalogTests(unittest.TestCase):
    def test_catalog_documents_exist(self) -> None:
        self.assertTrue(Path("docs/mcp_skill_catalog.md").is_file())
        self.assertTrue(Path("config/mcp_catalog.toml").is_file())

    def test_prepared_skills_load(self) -> None:
        skills = SkillLoader("skills").load_all()
        names = {skill.name for skill in skills}

        self.assertIn("repo-inspect", names)
        self.assertIn("coding-loop", names)
        self.assertIn("web-research", names)
        self.assertIn("gmail-newsletter-analysis", names)
        self.assertIn("obsidian-knowledge-linking", names)
        self.assertIn("browser-watcher", names)
        self.assertIn("mcp-safety-review", names)
        self.assertIn("credential-handling", names)

    def test_mcp_catalog_is_disabled_by_default(self) -> None:
        text = Path("config/mcp_catalog.toml").read_text(encoding="utf-8")

        self.assertIn("default_enabled = false", text)
        self.assertIn("[servers.playwright]", text)
        self.assertIn("[servers.gmail]", text)
        self.assertIn("[servers.obsidian]", text)


if __name__ == "__main__":
    unittest.main()
