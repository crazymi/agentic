from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    event_type: str
    payload: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "event_type": self.event_type,
                "payload": self.payload,
            },
            ensure_ascii=False,
            sort_keys=True,
        )


class TraceLogger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, payload: dict[str, Any]) -> TraceEvent:
        event = TraceEvent(event_type=event_type, payload=payload)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(event.to_json() + "\n")
        return event

    def read_events(self) -> list[TraceEvent]:
        events: list[TraceEvent] = []
        if not self.path.exists():
            return events
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                data = json.loads(line)
                events.append(
                    TraceEvent(
                        timestamp=data["timestamp"],
                        event_type=data["event_type"],
                        payload=data["payload"],
                    )
                )
        return events
