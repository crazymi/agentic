from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic.config.settings import load_app_config, load_dotenv
from agentic.prompts.builder import PromptBuilder
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry


class ConfigAndPromptTests(unittest.TestCase):
    def test_dotenv_loader_sets_values_without_overriding_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv = Path(tmpdir) / ".env"
            dotenv.write_text(
                "EXISTING=from_file\n"
                "PLAIN=value\n"
                "export QUOTED=\"hello world\"\n"
                "COMMENTED=ok # trailing comment\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"EXISTING": "from_env"}, clear=True):
                loaded = load_dotenv(dotenv)

                self.assertEqual(os.environ["EXISTING"], "from_env")
                self.assertEqual(os.environ["PLAIN"], "value")
                self.assertEqual(os.environ["QUOTED"], "hello world")
                self.assertEqual(os.environ["COMMENTED"], "ok")
                self.assertNotIn("EXISTING", loaded)

    def test_load_app_config_loads_project_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "config").mkdir()
            (root / ".env").write_text("AGENTIC_TEST_DOTENV=loaded\n", encoding="utf-8")
            (root / "config" / "config.toml").write_text(
                "[project]\n"
                "package_manager = \"uv\"\n"
                "venv = \".venv\"\n"
                "[paths]\n"
                "prompt_dir = \"prompts\"\n"
                "model_dir = \"models\"\n"
                "trace_dir = \"traces\"\n"
                "[prompts]\n"
                "master = \"prompts/master.md\"\n"
                "subagent = \"prompts/subagent.md\"\n"
                "tool_call_grammar = \"prompts/tool_call_grammar.md\"\n"
                "[runtime]\n"
                "default_master_model = \"\"\n"
                "default_subagent_model = \"\"\n"
                "trace_file = \"traces/phase0.jsonl\"\n"
                "[models]\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = load_app_config(root / "config" / "config.toml")

                self.assertEqual(config.root, root)
                self.assertEqual(os.environ["AGENTIC_TEST_DOTENV"], "loaded")

    def test_config_loads_uv_project_and_model_candidates(self) -> None:
        config = load_app_config()

        self.assertEqual(config.package_manager, "uv")
        self.assertTrue(config.venv.exists())
        self.assertEqual(
            set(config.models),
            {
                "master-gemma-q4",
                "master-gemma-iq2",
                "subagent-gemma-iq2",
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

        self.assertIn("master agent", master_prompt)
        self.assertIn("Tool calls must be strict JSON", subagent_prompt)
        self.assertIn('"name": "add"', subagent_prompt)
        self.assertIn('"name": "skill_workshop"', subagent_prompt)

        subagent_user_prompt = builder.subagent_user_prompt(
            SubAgentTask("compute"),
            ToolRegistry.with_defaults().schemas(),
        )
        self.assertNotIn("<system>", subagent_user_prompt)
        self.assertIn('"name": "add"', subagent_user_prompt)


if __name__ == "__main__":
    unittest.main()
