from __future__ import annotations

import json
from pathlib import Path

from agentic.connectors.gmail.models import EmailMessage


class FixtureGmailConnector:
    connector_id = "gmail-fixture"

    def __init__(self, messages: list[EmailMessage]):
        self.messages = messages

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "FixtureGmailConnector":
        messages = []
        with Path(path).open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                raw = json.loads(line)
                messages.append(EmailMessage(**raw))
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
