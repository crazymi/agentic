from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentic.tasks.state_machine import utc_now


class ResourceKind(StrEnum):
    EMAIL = "email"
    NOTE = "note"
    WEBPAGE = "webpage"
    FILE = "file"
    SCREENSHOT = "screenshot"


@dataclass(frozen=True)
class ResourceRecord:
    uri: str
    kind: ResourceKind
    title: str
    content_text: str
    source_connector: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)
    resource_id: str = field(default_factory=lambda: f"res_{uuid4().hex}")
    created_at: str = field(default_factory=utc_now)


class ResourceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(self, record: ResourceRecord) -> ResourceRecord:
        with self._connect() as conn:
            conn.execute(
                """
                insert into resources (
                    resource_id, uri, kind, title, content_text,
                    source_connector, metadata_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.resource_id,
                    record.uri,
                    record.kind.value,
                    record.title,
                    record.content_text,
                    record.source_connector,
                    json.dumps(record.metadata, ensure_ascii=False, sort_keys=True),
                    record.created_at,
                ),
            )
        return record

    def get(self, resource_id: str) -> ResourceRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select * from resources where resource_id = ?",
                (resource_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown resource id: {resource_id}")
        return self._record(row)

    def search(self, query: str, *, limit: int = 20) -> list[ResourceRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from resources where content_text like ? or title like ? order by created_at desc limit ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [self._record(row) for row in rows]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists resources (
                    resource_id text primary key,
                    uri text not null,
                    kind text not null,
                    title text not null,
                    content_text text not null,
                    source_connector text not null,
                    metadata_json text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _record(self, row: sqlite3.Row) -> ResourceRecord:
        return ResourceRecord(
            resource_id=row["resource_id"],
            uri=row["uri"],
            kind=ResourceKind(row["kind"]),
            title=row["title"],
            content_text=row["content_text"],
            source_connector=row["source_connector"],
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
        )
