from __future__ import annotations

import unittest
from pathlib import Path

from agentic.config.settings import load_app_config
from agentic.prompts.builder import PromptBuilder
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry


class ConfigAndPromptTests(unittest.TestCase):
    def test_config_loads_uv_project_and_model_candidates(self) -> None:
        config = load_app_config()

        self.assertEqual(config.package_manager, "uv")
        self.assertTrue(config.venv.exists())
        self.assertEqual(
            set(config.models),
            {
                "master-gemma-q4",
                "master-gemma-iq2",
                "subagent-diffusiongemma-q4",
            },
        )

    def test_configured_model_paths_exist(self) -> None:
        config = load_app_config()

        for model in config.models.values():
            with self.subTest(model=model.model_id):
                self.assertTrue(model.model_path)
                self.assertTrue(Path(model.model_path).exists())

    def test_prompt_builder_loads_prompt_directory_files(self) -> None:
        config = load_app_config()
        builder = PromptBuilder.from_files(
            config.prompts.master,
            config.prompts.subagent,
            config.prompts.tool_call_grammar,
        )

        master_prompt = builder.master_prompt("hello")
        subagent_prompt = builder.subagent_prompt(
            SubAgentTask("compute"),
            ToolRegistry.with_defaults().schemas(),
        )

        self.assertIn("Phase 1 master agent", master_prompt)
        self.assertIn("Tool calls must be strict JSON", subagent_prompt)
        self.assertIn('"name": "add"', subagent_prompt)

        subagent_user_prompt = builder.subagent_user_prompt(
            SubAgentTask("compute"),
            ToolRegistry.with_defaults().schemas(),
        )
        self.assertNotIn("<system>", subagent_user_prompt)
        self.assertIn('"name": "add"', subagent_user_prompt)


if __name__ == "__main__":
    unittest.main()
