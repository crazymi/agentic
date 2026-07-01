from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.config.settings import load_app_config
from agentic.experience import ExperienceEvent, ExperienceEventType, ExperienceStore, run_requirement_smoke


class ExperienceLoopTests(unittest.TestCase):
    def test_experience_store_appends_and_reads_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "experience.jsonl"
            store = ExperienceStore(path)
            store.append(
                ExperienceEvent(
                    event_type=ExperienceEventType.LESSON,
                    subject="probe",
                    summary="learned something",
                    evidence={"ok": True},
                    lessons=["keep it structured"],
                    tags=["test"],
                )
            )
            events = store.list()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].subject, "probe")
        self.assertEqual(events[0].lessons, ["keep it structured"])

    def test_requirement_smoke_covers_user_shaped_probes_and_records_experience(self) -> None:
        config = load_app_config("config/config.toml")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = run_requirement_smoke(
                config,
                state_dir=root / "state",
                experience_path=root / "experience.jsonl",
            )
            events = ExperienceStore(root / "experience.jsonl").list(limit=20)

        records = [item.to_record() for item in result.results]
        probe_ids = {record["probe_id"] for record in records}
        self.assertTrue(result.ok)
        self.assertEqual(len(records), 6)
        self.assertEqual(len(events), 6)
        self.assertIn("browser_ticket_transaction", probe_ids)
        browser = next(record for record in records if record["probe_id"] == "browser_ticket_transaction")
        self.assertEqual(browser["level"], "blocked_by_tooling")
        self.assertTrue(
            any(item["capability"] == "connector:browser" for item in browser["tooling_requests"])
        )

