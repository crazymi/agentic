from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from agentic.traces.logger import TraceEvent


@dataclass(frozen=True)
class TraceReplay:
    events: list[TraceEvent]

    @classmethod
    def from_path(cls, path: str | Path) -> "TraceReplay":
        events: list[TraceEvent] = []
        trace_path = Path(path)
        if not trace_path.exists():
            return cls(events)

        with trace_path.open("r", encoding="utf-8") as file:
            for line in file:
                data = json.loads(line)
                events.append(
                    TraceEvent(
                        event_type=data["event_type"],
                        payload=data["payload"],
                        timestamp=data["timestamp"],
                    )
                )
        return cls(events)

    def event_types(self) -> list[str]:
        return [event.event_type for event in self.events]

    def filter_by_type(self, event_type: str) -> list[TraceEvent]:
        return [event for event in self.events if event.event_type == event_type]

    def last_event(self, event_type: str | None = None) -> TraceEvent | None:
        if event_type is None:
            return self.events[-1] if self.events else None

        for event in reversed(self.events):
            if event.event_type == event_type:
                return event
        return None

    def assert_ordered_events(self, expected_event_types: Sequence[str]) -> None:
        cursor = 0
        actual = self.event_types()

        for expected in expected_event_types:
            try:
                found = actual.index(expected, cursor)
            except ValueError as exc:
                remaining = actual[cursor:]
                raise AssertionError(
                    f"missing expected event {expected!r} at or after index "
                    f"{cursor}; remaining events: {remaining!r}"
                ) from exc
            cursor = found + 1
