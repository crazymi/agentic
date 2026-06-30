from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.memory.models import MemoryKind, MemoryRecord
from agentic.tasks.state_machine import utc_now


class MemoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(
        self,
        *,
        kind: MemoryKind | str,
        text: str,
        tags: list[str] | None = None,
        source: str = "local",
        links: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            kind=MemoryKind(kind),
            text=text,
            tags=tags or [],
            source=source,
            links=links or [],
            metadata=metadata or {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                insert into memories (
                    memory_id, kind, text, tags_json, source, links_json,
                    metadata_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.kind.value,
                    record.text,
                    json.dumps(record.tags, ensure_ascii=False),
                    record.source,
                    json.dumps(record.links, ensure_ascii=False),
                    json.dumps(record.metadata, ensure_ascii=False, sort_keys=True),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def get(self, memory_id: str) -> MemoryRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select * from memories where memory_id = ?",
                (memory_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown memory id: {memory_id}")
        return self._record(row)

    def search(
        self,
        query: str = "",
        *,
        kind: MemoryKind | str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[MemoryRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            clauses.append("text like ?")
            params.append(f"%{query}%")
        if kind is not None:
            clauses.append("kind = ?")
            params.append(MemoryKind(kind).value)
        if tag is not None:
            clauses.append("tags_json like ?")
            params.append(f"%{tag}%")
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select * from memories{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [self._record(row) for row in rows]

    def standing_goals(self) -> list[MemoryRecord]:
        return self.search(kind=MemoryKind.STANDING_GOAL, limit=100)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists memories (
                    memory_id text primary key,
                    kind text not null,
                    text text not null,
                    tags_json text not null,
                    source text not null,
                    links_json text not null,
                    metadata_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["memory_id"],
            kind=MemoryKind(row["kind"]),
            text=row["text"],
            tags=json.loads(row["tags_json"]),
            source=row["source"],
            links=json.loads(row["links_json"]),
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
