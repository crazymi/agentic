from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    received_at: str
    body_text: str
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def uri(self) -> str:
        return f"gmail://message/{self.message_id}"
