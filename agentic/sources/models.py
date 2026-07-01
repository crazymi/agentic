from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_id() -> str:
    return f"src_{uuid4().hex}"


def source_item_id() -> str:
    return f"sitem_{uuid4().hex}"


class SourceKind(StrEnum):
    WEB_PAGE = "web_page"
    FEED = "feed"
    MAIL = "mail"
    BROWSER_PAGE = "browser_page"
    LOCAL_FILE = "local_file"
    REPO_STATE = "repo_state"


@dataclass(frozen=True)
class SourcePolicy:
    read_only: bool = True
    requires_approval: bool = False
    rate_limit_seconds: int = 60
    retention_days: int = 30
    dedupe_fields: list[str] = field(default_factory=lambda: ["uri", "title", "content_text"])

    def __post_init__(self) -> None:
        if self.rate_limit_seconds < 0:
            raise ValueError("rate_limit_seconds must be non-negative")
        if self.retention_days < 0:
            raise ValueError("retention_days must be non-negative")

    def to_record(self) -> dict[str, Any]:
        return {
            "read_only": self.read_only,
            "requires_approval": self.requires_approval,
            "rate_limit_seconds": self.rate_limit_seconds,
            "retention_days": self.retention_days,
            "dedupe_fields": self.dedupe_fields,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "SourcePolicy":
        record = record or {}
        return cls(
            read_only=bool(record.get("read_only", True)),
            requires_approval=bool(record.get("requires_approval", False)),
            rate_limit_seconds=int(record.get("rate_limit_seconds", 60)),
            retention_days=int(record.get("retention_days", 30)),
            dedupe_fields=list(record.get("dedupe_fields") or ["uri", "title", "content_text"]),
        )


@dataclass(frozen=True)
class SourceDefinition:
    kind: SourceKind
    name: str
    locator: str
    source_id: str = field(default_factory=source_id)
    connector_id: str = ""
    credential_ref: str | None = None
    enabled: bool = False
    policy: SourcePolicy = field(default_factory=SourcePolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", SourceKind(self.kind))
        if not self.name:
            raise ValueError("source name must not be empty")
        if not self.locator:
            raise ValueError("source locator must not be empty")
        _reject_secret_payload(self.metadata)

    def to_record(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "kind": self.kind.value,
            "name": self.name,
            "locator": self.locator,
            "connector_id": self.connector_id,
            "credential_ref": self.credential_ref,
            "enabled": self.enabled,
            "policy": self.policy.to_record(),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SourceDefinition":
        return cls(
            source_id=str(record["source_id"]),
            kind=SourceKind(record["kind"]),
            name=str(record["name"]),
            locator=str(record["locator"]),
            connector_id=str(record.get("connector_id") or ""),
            credential_ref=record.get("credential_ref"),
            enabled=bool(record.get("enabled", False)),
            policy=SourcePolicy.from_record(record.get("policy")),
            metadata=dict(record.get("metadata") or {}),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )


@dataclass(frozen=True)
class SourceItem:
    source_id: str
    uri: str
    title: str
    content_text: str
    item_id: str = field(default_factory=source_item_id)
    fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    collected_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        if not self.uri:
            raise ValueError("source item uri must not be empty")
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", fingerprint_item(self))
        _reject_secret_payload(self.metadata)

    def to_record(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "uri": self.uri,
            "title": self.title,
            "content_text": self.content_text,
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
            "collected_at": self.collected_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SourceItem":
        return cls(
            item_id=str(record["item_id"]),
            source_id=str(record["source_id"]),
            uri=str(record["uri"]),
            title=str(record.get("title") or ""),
            content_text=str(record.get("content_text") or ""),
            fingerprint=str(record.get("fingerprint") or ""),
            metadata=dict(record.get("metadata") or {}),
            collected_at=str(record.get("collected_at") or utc_now()),
        )


class SourceCollector(Protocol):
    def collect(self, source: SourceDefinition) -> list[SourceItem]:
        ...


def fingerprint_item(item: SourceItem) -> str:
    payload = "\n".join([item.source_id, item.uri, item.title, item.content_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reject_secret_payload(payload: dict[str, Any]) -> None:
    forbidden = {"secret", "token", "password", "credential", "api_key", "apikey", "value"}
    for key in payload:
        lowered = str(key).lower()
        if lowered in forbidden or any(word in lowered for word in forbidden):
            raise ValueError(f"metadata must not contain secret-like key: {key}")
