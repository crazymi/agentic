from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.connectors.gmail import FixtureGmailConnector
from agentic.memory.store import MemoryStore
from agentic.resources.store import ResourceStore
from agentic.workflows.newsletter import NewsletterAnalysisGoal, NewsletterWorkflow


class Milestone7NewsletterTests(unittest.TestCase):
    def test_fixture_gmail_connector_finds_wsj_newsletter(self) -> None:
        connector = FixtureGmailConnector.from_jsonl("evals/fixtures/wsj_newsletter.jsonl")

        messages = connector.search_newsletters(query="WSJ")

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message_id, "wsj-1")

    def test_newsletter_workflow_ingests_resources_and_generates_grounded_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            connector = FixtureGmailConnector.from_jsonl("evals/fixtures/wsj_newsletter.jsonl")
            resources = ResourceStore(Path(tmpdir) / "resources.sqlite3")
            memory = MemoryStore(Path(tmpdir) / "memory.sqlite3")
            workflow = NewsletterWorkflow(resources=resources, memory=memory)
            goal = NewsletterAnalysisGoal(
                name="startup and portfolio scan",
                description="Find startup ideas and portfolio/stock relevance.",
                tags=["startup", "portfolio"],
            )

            report = workflow.run(connector.search_newsletters(query="WSJ"), goal)
            insights = memory.search("Newsletter Report")

        self.assertGreaterEqual(len(report.findings), 2)
        self.assertTrue(any(item.kind == "startup_idea" for item in report.findings))
        self.assertTrue(any(item.kind == "portfolio_relevance" for item in report.findings))
        self.assertTrue(all(item.source_uri.startswith("gmail://message/") for item in report.findings))
        self.assertEqual(len(insights), 1)


if __name__ == "__main__":
    unittest.main()
