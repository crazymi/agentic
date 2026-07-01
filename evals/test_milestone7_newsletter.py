from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from agentic.connectors.gmail.models import EmailMessage
from agentic.memory.store import MemoryStore
from agentic.resources.store import ResourceStore
from agentic.workflows.newsletter import NewsletterAnalysisGoal, NewsletterWorkflow


class Milestone7NewsletterTests(unittest.TestCase):
    def test_jsonl_mailbox_finds_wsj_newsletter(self) -> None:
        connector = _JsonlMailbox.from_jsonl("evals/fixtures/wsj_newsletter.jsonl")

        messages = connector.search_newsletters(query="WSJ")

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message_id, "wsj-1")

    def test_newsletter_workflow_ingests_resources_and_generates_grounded_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            connector = _JsonlMailbox.from_jsonl("evals/fixtures/wsj_newsletter.jsonl")
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


class _JsonlMailbox:
    def __init__(self, messages: list[EmailMessage]):
        self.messages = messages

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "_JsonlMailbox":
        messages = []
        with Path(path).open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                messages.append(EmailMessage(**json.loads(line)))
        return cls(messages)

    def search_newsletters(self, *, query: str = "WSJ") -> list[EmailMessage]:
        lowered = query.lower()
        return [
            message
            for message in self.messages
            if lowered in message.subject.lower()
            or lowered in message.sender.lower()
            or lowered in message.body_text.lower()
        ]


if __name__ == "__main__":
    unittest.main()
