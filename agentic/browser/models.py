from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BrowserObservation:
    url: str
    title: str
    state: str
    visible_text: str
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "state": self.state,
            "visible_text": self.visible_text,
            "actions": self.actions,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BrowserActionResult:
    action: str
    status: str
    state: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "state": self.state,
            "message": self.message,
            "metadata": self.metadata,
        }
