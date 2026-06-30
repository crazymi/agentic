from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.memory import MemoryKind, MemoryStore, capture_idea
from agentic.memory.standing_orders import add_standing_goal, standing_goal_prompt_context
from agentic.resources.obsidian import ObsidianLocalConnector
from agentic.resources.store import ResourceKind, ResourceRecord, ResourceStore
from agentic.synthesis import synthesize_ideas


class Milestone6MemoryTests(unittest.TestCase):
    def test_idea_capture_survives_restart_and_searches_by_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.sqlite3"
            store = MemoryStore(path)
            captured = capture_idea(store, "AI memory app idea", source="chat")
            reloaded = MemoryStore(path)
            matches = reloaded.search("memory", kind=MemoryKind.IDEA, tag="memory")

        self.assertEqual(matches[0].memory_id, captured.memory.memory_id)
        self.assertEqual(captured.followup_question.kind, MemoryKind.FOLLOWUP_QUESTION)

    def test_standing_goal_prompt_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.sqlite3")
            add_standing_goal(store, "Find startup ideas in newsletters.")

            context = standing_goal_prompt_context(store)

        self.assertIn("Find startup ideas", context)

    def test_resource_store_keeps_citation_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResourceStore(Path(tmpdir) / "resources.sqlite3")
            resource = store.add(
                ResourceRecord(
                    uri="email://wsj/1",
                    kind=ResourceKind.EMAIL,
                    title="WSJ",
                    content_text="AI market signal",
                    source_connector="gmail",
                    metadata={"message_id": "1"},
                )
            )
            matches = store.search("market")

        self.assertEqual(matches[0].resource_id, resource.resource_id)
        self.assertEqual(matches[0].metadata["message_id"], "1")

    def test_obsidian_connector_writes_reversible_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.sqlite3")
            memory = capture_idea(store, "Obsidian linked idea").memory
            connector = ObsidianLocalConnector(Path(tmpdir) / "vault")

            note = connector.write_memory_note(memory)
            note_text = note.read_text(encoding="utf-8")

        self.assertTrue(note.name.endswith(".md"))
        self.assertIn(memory.memory_id, note_text)

    def test_synthesis_references_multiple_ideas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.sqlite3")
            capture_idea(store, "agent memory idea")
            capture_idea(store, "browser agent idea")

            result = synthesize_ideas(store, query="idea")

        self.assertEqual(result["source_count"], 2)
        self.assertIn("Found 2", result["insight"])


if __name__ == "__main__":
    unittest.main()
