from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def delivery_id() -> str:
    return f"del_{uuid4().hex}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class DeliveryChannel(StrEnum):
    NTFY = "ntfy"


@dataclass(frozen=True)
class DeliveryRecord:
    artifact_id: str
    channel: DeliveryChannel | str
    title: str
    body: str
    destination: str = ""
    delivery_id: str = field(default_factory=delivery_id)
    status: DeliveryStatus | str = DeliveryStatus.PENDING
    attempts: int = 0
    error: dict[str, Any] | None = None
    sent_at: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.channel, str):
            object.__setattr__(self, "channel", DeliveryChannel(self.channel))
        if isinstance(self.status, str):
            object.__setattr__(self, "status", DeliveryStatus(self.status))
        if not self.artifact_id:
            raise ValueError("delivery artifact_id must not be empty")
        if not self.title:
            raise ValueError("delivery title must not be empty")
        if not self.body:
            raise ValueError("delivery body must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "artifact_id": self.artifact_id,
            "channel": self.channel.value,
            "destination": self.destination,
            "status": self.status.value,
            "title": self.title,
            "body": self.body,
            "attempts": self.attempts,
            "error": self.error,
            "sent_at": self.sent_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "DeliveryRecord":
        return cls(
            delivery_id=str(record["delivery_id"]),
            artifact_id=str(record["artifact_id"]),
            channel=DeliveryChannel(record["channel"]),
            destination=str(record.get("destination") or ""),
            status=DeliveryStatus(record.get("status", DeliveryStatus.PENDING.value)),
            title=str(record.get("title") or ""),
            body=str(record.get("body") or ""),
            attempts=int(record.get("attempts") or 0),
            error=record.get("error"),
            sent_at=record.get("sent_at"),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )
