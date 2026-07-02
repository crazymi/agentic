from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.config.settings import load_app_config
from agentic.probes.finish_line import run_frontdoor_finish_line_benchmark


class FinishLineBenchmarkTests(unittest.TestCase):
    def test_multi_turn_frontdoor_benchmark_reaches_report_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            html = root / "community.html"
            html.write_text(
                """
                <html><body>
                  <a href="post-1">AI 반도체 수요가 강하다는 글</a>
                  <a href="post-2">미국 주식 투자 심리 변화 관찰</a>
                  <a href="post-3">환율과 기술주 변동성 토론</a>
                </body></html>
                """,
                encoding="utf-8",
            )

            result = run_frontdoor_finish_line_benchmark(
                load_app_config("config/config.toml"),
                state_dir=root / "state",
                request="반복 자동화 하나 만들어서 나한테 ntfy 알림 보내줘",
                answers=[
                    "주식갤을 소스로 써. 투자 아이디어와 시장 심리를 보고 싶어.",
                    "1분마다 수집하고 1시간마다 최근 글을 트렌드 보고서로 보내줘.",
                ],
                source_url=html.as_uri(),
                source_aliases=["community_web", "주식갤"],
                require_delivery=False,
            )

        self.assertTrue(result.ok, result.to_record())
        self.assertGreaterEqual(result.session_event_types.count("interview_answer"), 2)
        self.assertTrue(result.workflow_id.startswith("wf_"))
        self.assertTrue(result.session_id.startswith("sess_"))
        self.assertTrue(result.artifact_ids)
        self.assertTrue(result.report_quality.get("ok"), result.to_record())
        self.assertGreaterEqual(result.score_0_100, 98)


if __name__ == "__main__":
    unittest.main()
