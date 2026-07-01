from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.config.settings import load_app_config
from agentic.ops import run_operational_smoke


class Milestone10OpsSmokeTests(unittest.TestCase):
    def test_operational_smoke_runs_source_bound_workflow(self) -> None:
        config = load_app_config("config/config.toml")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_operational_smoke(config, state_dir=tmpdir)

            check_by_name = {check.name: check for check in result.checks}

        self.assertTrue(result.ok)
        self.assertTrue(check_by_name["workflow_source_bound"].ok)
        self.assertIn("market_community_posts.jsonl", check_by_name["workflow_source_bound"].detail)
        self.assertTrue(check_by_name["workflow_run_completed"].ok)
        self.assertIn("collected=3", check_by_name["workflow_run_completed"].detail)
        self.assertTrue(check_by_name["report_artifact_created"].ok)
        self.assertTrue(Path(tmpdir).exists() is False)


if __name__ == "__main__":
    unittest.main()
