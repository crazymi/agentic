from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.runtime.task_pool import TaskPool
from agentic.runtime.task_router import TaskRouter
from agentic.sources import SourceDefinition, SourceKind, SourceStore
from agentic.sources.strategy import source_strategy_tuning_request
from agentic.sources.strategy_recovery import (
    SOURCE_STRATEGY_RECOVERY_TASK_KIND,
    SourceStrategyRecoveryExecutor,
    SourceStrategyRecoveryService,
)
from agentic.sources.strategy_workshop import (
    SourceStrategyProposalStore,
    SourceStrategyProposalStatus,
)
from agentic.tasks.store import TaskStore
from agentic.tooling import ToolingBacklogStore, ToolingStatus


class SourceStrategyRecoveryTests(unittest.TestCase):
    def test_recover_tooling_proposes_and_applies_safe_source_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            proposal_store = SourceStrategyProposalStore(root / "source_strategy.sqlite3")
            source = _source(source_store)
            tooling = _tooling(tooling_store, source.source_id)

            result = SourceStrategyRecoveryService(
                source_store=source_store,
                proposal_store=proposal_store,
                tooling_store=tooling_store,
            ).recover_tooling(tooling.tooling_id, rerun=False)
            proposal = proposal_store.get(result.proposal_id)
            updated = source_store.get_source(source.source_id)
            request = tooling_store.get(tooling.tooling_id)

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "applied")
        self.assertEqual(proposal.status, SourceStrategyProposalStatus.APPLIED)
        self.assertIn("/board/view", updated.metadata["extract"]["href_contains"])
        self.assertIn("id=stock", updated.metadata["extract"]["href_contains_all"])
        self.assertGreaterEqual(updated.metadata["quality"]["min_items"], 3)
        self.assertEqual(request.status, ToolingStatus.IN_PROGRESS)

    def test_recover_pending_can_create_proposals_without_auto_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            proposal_store = SourceStrategyProposalStore(root / "source_strategy.sqlite3")
            source = _source(source_store)
            tooling = _tooling(tooling_store, source.source_id)

            results = SourceStrategyRecoveryService(
                source_store=source_store,
                proposal_store=proposal_store,
                tooling_store=tooling_store,
            ).recover_pending(auto_apply=False)
            proposal = proposal_store.get(results[0].proposal_id)
            request = tooling_store.get(tooling.tooling_id)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].status, "proposed")
        self.assertEqual(proposal.status, SourceStrategyProposalStatus.PENDING)
        self.assertEqual(request.status, ToolingStatus.PROPOSED)

    def test_recovery_executor_runs_as_durable_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            tooling_store = ToolingBacklogStore(root / "tooling.sqlite3")
            source = _source(source_store)
            tooling = _tooling(tooling_store, source.source_id)
            task_store = TaskStore(root / "agentic.sqlite3")
            pool = TaskPool(
                store=task_store,
                executor=TaskRouter(
                    {
                        SOURCE_STRATEGY_RECOVERY_TASK_KIND: SourceStrategyRecoveryExecutor(
                            default_state_dir=root,
                        )
                    }
                ),
                max_workers=1,
                heartbeat_interval_s=0,
            )
            task = task_store.create_task(
                kind=SOURCE_STRATEGY_RECOVERY_TASK_KIND,
                input={
                    "state_dir": str(root),
                    "tooling_id": tooling.tooling_id,
                    "rerun": False,
                },
            )

            pool.kick()
            pool.shutdown(wait=True)
            completed = task_store.get_task(task.task_id)

        self.assertEqual(completed.status.value, "completed")
        self.assertTrue(completed.result["ok"])
        self.assertEqual(completed.result["results"][0]["status"], "applied")


def _source(store: SourceStore):
    return store.add_source(
        SourceDefinition(
            kind=SourceKind.WEB_PAGE,
            name="Forum list",
            locator="https://example.com/board/lists/?id=stock",
            enabled=True,
            metadata={"extract": {"limit": 5}},
        )
    )


def _tooling(store: ToolingBacklogStore, source_id: str):
    return store.add(
        source_strategy_tuning_request(
            workflow_id="wf_1",
            run_id="run_1",
            reports=[
                {
                    "source_id": source_id,
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


if __name__ == "__main__":
    unittest.main()
