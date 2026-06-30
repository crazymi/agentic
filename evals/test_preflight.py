from __future__ import annotations

import unittest

from agentic.config.settings import load_app_config
from agentic.runtime.preflight import run_preflight


class PreflightTests(unittest.TestCase):
    def test_preflight_reports_model_paths_and_executables(self) -> None:
        results = run_preflight(load_app_config())
        names = {result.name for result in results}

        self.assertIn("model_path:master-gemma-q4", names)
        self.assertIn("model_path:master-gemma-iq2", names)
        self.assertIn("model_path:subagent-diffusiongemma-q4", names)
        self.assertIn("executable:master-gemma-q4", names)
        self.assertIn("executable:subagent-diffusiongemma-q4", names)


if __name__ == "__main__":
    unittest.main()
