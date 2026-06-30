from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from agentic.runtime.events import InboundMessage


@dataclass(frozen=True)
class ChannelMessage:
    text: str
    channel: str
    message_id: str = field(default_factory=lambda: f"out_{uuid4().hex}")


class Channel(Protocol):
    def send_message(self, message: ChannelMessage) -> None:
        ...

    def receive_message(self) -> InboundMessage | None:
        ...
