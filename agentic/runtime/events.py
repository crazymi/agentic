from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from agentic.traces.logger import TraceLogger


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_id() -> str:
    return f"evt_{uuid4().hex}"


def _message_id() -> str:
    return f"msg_{uuid4().hex}"


def ensure_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be JSON-compatible") from exc
    return dict(payload)


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: str
    source: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=_event_id)
    created_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not self.source:
            raise ValueError("source must not be empty")
        object.__setattr__(self, "payload", ensure_json_payload(self.payload))

    def trace_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "created_at": self.created_at,
            **self.payload,
        }


@dataclass(frozen=True)
class InboundMessage:
    text: str
    channel: str = "web"
    user_id: str = "local-user"
    message_id: str = field(default_factory=_message_id)
    created_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id must not be empty")
        if not self.channel:
            raise ValueError("channel must not be empty")

    def to_event(self) -> RuntimeEvent:
        return RuntimeEvent(
            event_type="channel_message_received",
            source=self.channel,
            payload={
                "message_id": self.message_id,
                "user_id": self.user_id,
                "text": self.text,
                "message_created_at": self.created_at,
            },
        )


class TraceRecorder(Protocol):
    def record(self, event_type: str, payload: dict[str, Any]) -> object:
        ...


def record_channel_message(
    trace: TraceLogger | TraceRecorder,
    message: InboundMessage,
) -> RuntimeEvent:
    event = message.to_event()
    trace.record(event.event_type, event.trace_payload())
    return event
