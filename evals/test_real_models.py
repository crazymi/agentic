from __future__ import annotations

import os
import unittest

from dataclasses import replace

from agentic.config.settings import load_app_config
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry


RUN_REAL_MODELS = os.getenv("AGENTIC_RUN_REAL_MODELS") == "1"


@unittest.skipUnless(RUN_REAL_MODELS, "set AGENTIC_RUN_REAL_MODELS=1 to run local GGUF model evals")
class RealModelSmokeTests(unittest.TestCase):
    def test_all_configured_models_answer_capital_question(self) -> None:
        config = load_app_config()
        builder = PromptBuilder.from_files(
            config.prompts.master,
            config.prompts.subagent,
            config.prompts.tool_call_grammar,
        )
        prompt = "한국의 수도는 어디야? 답변만 한 문장으로 말해."

        for model_id in (
            "master-gemma-q4",
            "master-gemma-iq2",
            "subagent-diffusiongemma-q4",
        ):
            with self.subTest(model_id=model_id):
                model = replace(config.model(model_id), max_tokens=384)
                if model.role == "subagent":
                    full_prompt = builder.subagent_user_prompt(
                        SubAgentTask(prompt),
                        ToolRegistry.with_defaults().schemas(),
                    )
                else:
                    full_prompt = prompt

                response = LocalGGUFProvider(model).generate(full_prompt)

                self.assertIn("서울", response.text)


if __name__ == "__main__":
    unittest.main()
