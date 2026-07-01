from __future__ import annotations

import json
from pathlib import Path

from agentic.experience.models import ExperienceEvent


class ExperienceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: ExperienceEvent) -> ExperienceEvent:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_record(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return event

    def list(self, *, limit: int = 100) -> list[ExperienceEvent]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines[-limit:] if line.strip()]
        return [ExperienceEvent.from_record(record) for record in records]

