from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic.workflow_kernel.models import utc_now


def session_id() -> str:
    return f"sess_{uuid4().hex}"


def session_event_id() -> str:
    return f"sevt_{uuid4().hex}"


@dataclass(frozen=True)
class SessionRecord:
    title: str
    session_id: str = field(default_factory=session_id)
    status: str = "open"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not self.title:
            raise ValueError("session title must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SessionRecord":
        return cls(
            session_id=str(record["session_id"]),
            title=str(record["title"]),
            status=str(record.get("status") or "open"),
            metadata=dict(record.get("metadata") or {}),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )


@dataclass(frozen=True)
class SessionEvent:
    session_id: str
    event_type: str
    role: str = "runtime"
    content: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=session_event_id)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "role": self.role,
            "content": self.content,
            "payload": self.payload,
            "created_at": self.created_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SessionEvent":
        return cls(
            event_id=str(record["event_id"]),
            session_id=str(record["session_id"]),
            event_type=str(record["event_type"]),
            role=str(record.get("role") or "runtime"),
            content=str(record.get("content") or ""),
            payload=dict(record.get("payload") or {}),
            created_at=str(record.get("created_at") or utc_now()),
        )


class SessionLogStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def start_session(
        self,
        title: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> SessionRecord:
        record = SessionRecord(title=title, metadata=metadata or {})
        with self._connect() as conn:
            conn.execute(
                """
                insert into sessions (
                    session_id, status, record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    record.session_id,
                    record.status,
                    self._dump(record.to_record()),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def close_session(self, session_id: str, *, status: str = "closed") -> SessionRecord:
        current = self.get_session(session_id)
        updated = SessionRecord.from_record(
            {**current.to_record(), "status": status, "updated_at": utc_now()}
        )
        with self._connect() as conn:
            conn.execute(
                """
                update sessions
                set status = ?, record_json = ?, updated_at = ?
                where session_id = ?
                """,
                (updated.status, self._dump(updated.to_record()), updated.updated_at, session_id),
            )
        return updated

    def get_session(self, session_id: str) -> SessionRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from sessions where session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown session id: {session_id}")
        return SessionRecord.from_record(json.loads(row["record_json"]))

    def list_sessions(self, *, limit: int = 100) -> list[SessionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select record_json from sessions order by updated_at desc limit ?",
                (limit,),
            ).fetchall()
        return [SessionRecord.from_record(json.loads(row["record_json"])) for row in rows]

    def append_event(
        self,
        session_id: str,
        event_type: str,
        *,
        role: str = "runtime",
        content: str = "",
        payload: dict[str, Any] | None = None,
    ) -> SessionEvent:
        event = SessionEvent(
            session_id=session_id,
            event_type=event_type,
            role=role,
            content=content,
            payload=payload or {},
        )
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into session_events (
                    event_id, session_id, event_type, role, content, payload_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.event_type,
                    event.role,
                    event.content,
                    self._dump(event.payload),
                    event.created_at,
                ),
            )
            conn.execute(
                "update sessions set updated_at = ? where session_id = ?",
                (now, session_id),
            )
        return event

    def list_events(self, session_id: str, *, limit: int = 500) -> list[SessionEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select event_id, session_id, event_type, role, content, payload_json, created_at
                from session_events
                where session_id = ?
                order by id asc
                limit ?
                """,
                (session_id, limit),
            ).fetchall()
        return [
            SessionEvent.from_record(
                {
                    "event_id": row["event_id"],
                    "session_id": row["session_id"],
                    "event_type": row["event_type"],
                    "role": row["role"],
                    "content": row["content"],
                    "payload": json.loads(row["payload_json"]),
                    "created_at": row["created_at"],
                }
            )
            for row in rows
        ]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists sessions (
                    session_id text primary key,
                    status text not null,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists session_events (
                    id integer primary key autoincrement,
                    event_id text not null unique,
                    session_id text not null,
                    event_type text not null,
                    role text not null,
                    content text not null,
                    payload_json text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
