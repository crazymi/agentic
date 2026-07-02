from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.sources import SourceDefinition, SourceKind, SourceStore
from agentic.sources.strategy import source_strategy_tuning_request
from agentic.sources.strategy_workshop import (
    SourceStrategyProposalStatus,
    SourceStrategyProposalStore,
    SourceStrategyWorkshopService,
)
from agentic.tooling import ToolingBacklogStore, ToolingStatus


class SourceStrategyWorkshopTests(unittest.TestCase):
    def test_source_store_update_source_persists_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SourceStore(Path(tmpdir) / "sources.sqlite3")
            source = store.add_source(
                SourceDefinition(
                    kind=SourceKind.WEB_PAGE,
                    name="Forum list",
                    locator="https://example.com/board/lists/?id=x",
                    enabled=True,
                    metadata={"extract": {"limit": 5}},
                )
            )
            updated = SourceDefinition.from_record(
                {**source.to_record(), "metadata": {"extract": {"limit": 30}}}
            )

            store.update_source(updated)
            reloaded = store.get_source(source.source_id)

        self.assertEqual(reloaded.metadata["extract"]["limit"], 30)
        self.assertEqual(reloaded.created_at, source.created_at)
        self.assertNotEqual(reloaded.updated_at, source.updated_at)

    def test_propose_from_tooling_creates_reviewable_source_metadata_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            proposal_store = SourceStrategyProposalStore(root / "source_strategy.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.WEB_PAGE,
                    name="Forum list",
                    locator="https://example.com/board/lists/?id=stock",
                    enabled=True,
                    metadata={"extract": {"limit": 5}},
                )
            )
            tooling = tooling_store.add(
                source_strategy_tuning_request(
                    workflow_id="wf_1",
                    run_id="run_1",
                    reports=[
                        {
                            "source_id": source.source_id,
                            "item_count": 10,
                            "score": 47,
                            "ok": False,
                            "min_score": 55,
                            "min_items": 1,
                            "nav_like_count": 4,
                            "short_text_count": 4,
                            "duplicate_text_count": 0,
                            "off_path_count": 6,
                            "reasons": [
                                "navigation_like_items",
                                "off_source_path_items",
                                "score_below_threshold",
                            ],
                            "examples": [
                                "통합검색 바로가기",
                                "본문영역 바로가기",
                                "페이지 하단 게시물 리스트 바로가기",
                            ],
                        }
                    ],
                )
            )

            proposal = SourceStrategyWorkshopService(
                source_store=source_store,
                proposal_store=proposal_store,
                tooling_store=tooling_store,
            ).propose_from_tooling(tooling.tooling_id)

        self.assertEqual(proposal.source_id, source.source_id)
        self.assertEqual(proposal.status, SourceStrategyProposalStatus.PENDING)
        self.assertEqual(proposal.proposed_metadata["extract"]["limit"], 20)
        self.assertIn("/board/view", proposal.proposed_metadata["extract"]["href_contains"])
        self.assertIn("id=stock", proposal.proposed_metadata["extract"]["href_contains_all"])
        self.assertIn("바로가기", proposal.proposed_metadata["extract"]["text_excludes"])
        self.assertIn("이용 안내", proposal.proposed_metadata["extract"]["text_excludes"])
        self.assertIn(r"^\[[0-9]+\]$", proposal.proposed_metadata["extract"]["text_exclude_regexes"])
        self.assertIn("quality", proposal.proposed_metadata)
        self.assertGreaterEqual(proposal.proposed_metadata["quality"]["min_items"], 3)

    def test_apply_updates_source_and_marks_tooling_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            proposal_store = SourceStrategyProposalStore(root / "source_strategy.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.WEB_PAGE,
                    name="Forum list",
                    locator="https://example.com/board/lists/?id=stock",
                    enabled=True,
                    metadata={"extract": {"limit": 5}},
                )
            )
            tooling = tooling_store.add(
                source_strategy_tuning_request(
                    workflow_id="wf_1",
                    run_id="run_1",
                    reports=[
                        {
                            "source_id": source.source_id,
                            "item_count": 1,
                            "score": 20,
                            "ok": False,
                            "min_score": 55,
                            "min_items": 1,
                            "reasons": ["score_below_threshold"],
                            "examples": ["통합검색 바로가기"],
                        }
                    ],
                )
            )
            service = SourceStrategyWorkshopService(
                source_store=source_store,
                proposal_store=proposal_store,
                tooling_store=tooling_store,
            )
            proposal = service.propose_from_tooling(tooling.tooling_id)

            applied = service.apply(proposal.proposal_id)
            source_after = source_store.get_source(source.source_id)
            tooling_after = tooling_store.get(tooling.tooling_id)

        self.assertEqual(applied.status, SourceStrategyProposalStatus.APPLIED)
        self.assertIn("/board/view", source_after.metadata["extract"]["href_contains"])
        self.assertIn("id=stock", source_after.metadata["extract"]["href_contains_all"])
        self.assertEqual(tooling_after.status, ToolingStatus.IN_PROGRESS)


if __name__ == "__main__":
    unittest.main()
