from __future__ import annotations

import os
import unittest

from agentic.config.settings import load_app_config
from agentic.runtime.full_loop import FullLoopRuntime


RUN_REAL_PHASE1 = os.getenv("AGENTIC_RUN_REAL_PHASE1") == "1"


@unittest.skipUnless(RUN_REAL_PHASE1, "set AGENTIC_RUN_REAL_PHASE1=1 to run real Phase 1 loop")
class RealPhase1FullLoopTests(unittest.TestCase):
    def test_real_full_loop_answers_addition(self) -> None:
        runtime = FullLoopRuntime.from_config(load_app_config())

        result = runtime.run("1+1은 뭐지?")

        self.assertTrue(result.ok)
        self.assertIn("2", result.final_answer)


if __name__ == "__main__":
    unittest.main()
