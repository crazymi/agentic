from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.sources.models import SourceDefinition, SourceItem, SourceKind, utc_now


class SourceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add_source(self, source: SourceDefinition) -> SourceDefinition:
        with self._connect() as conn:
            conn.execute(
                """
                insert into source_definitions (
                    source_id, kind, enabled, record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (
                    source.source_id,
                    source.kind.value,
                    int(source.enabled),
                    self._dump(source.to_record()),
                    source.created_at,
                    source.updated_at,
                ),
            )
        return source

    def get_source(self, source_id: str) -> SourceDefinition:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from source_definitions where source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown source id: {source_id}")
        return SourceDefinition.from_record(json.loads(row["record_json"]))

    def list_sources(
        self,
        *,
        kind: SourceKind | str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
    ) -> list[SourceDefinition]:
        clauses: list[str] = []
        params: list[Any] = []
        if kind is not None:
            clauses.append("kind = ?")
            params.append(SourceKind(kind).value)
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(int(enabled))
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from source_definitions{where} order by updated_at desc limit ?",
                params,
            ).fetchall()
        return [SourceDefinition.from_record(json.loads(row["record_json"])) for row in rows]

    def set_enabled(self, source_id: str, enabled: bool) -> SourceDefinition:
        current = self.get_source(source_id)
        updated = SourceDefinition.from_record(
            {**current.to_record(), "enabled": enabled, "updated_at": utc_now()}
        )
        with self._connect() as conn:
            conn.execute(
                """
                update source_definitions
                set enabled = ?, record_json = ?, updated_at = ?
                where source_id = ?
                """,
                (int(enabled), self._dump(updated.to_record()), updated.updated_at, source_id),
            )
        return updated

    def update_source(self, source: SourceDefinition) -> SourceDefinition:
        current = self.get_source(source.source_id)
        updated = SourceDefinition.from_record(
            {
                **source.to_record(),
                "created_at": current.created_at,
                "updated_at": utc_now(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update source_definitions
                set kind = ?, enabled = ?, record_json = ?, updated_at = ?
                where source_id = ?
                """,
                (
                    updated.kind.value,
                    int(updated.enabled),
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    updated.source_id,
                ),
            )
        return updated

    def add_item_dedup(self, item: SourceItem) -> tuple[SourceItem, bool]:
        with self._connect() as conn:
            existing = conn.execute(
                "select record_json from source_items where source_id = ? and fingerprint = ?",
                (item.source_id, item.fingerprint),
            ).fetchone()
            if existing is not None:
                return SourceItem.from_record(json.loads(existing["record_json"])), False
            conn.execute(
                """
                insert into source_items (
                    item_id, source_id, fingerprint, uri, record_json, collected_at
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (
                    item.item_id,
                    item.source_id,
                    item.fingerprint,
                    item.uri,
                    self._dump(item.to_record()),
                    item.collected_at,
                ),
            )
        return item, True

    def list_items(
        self,
        *,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[SourceItem]:
        clauses: list[str] = []
        params: list[Any] = []
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from source_items{where} order by collected_at desc limit ?",
                params,
            ).fetchall()
        return [SourceItem.from_record(json.loads(row["record_json"])) for row in rows]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists source_definitions (
                    source_id text primary key,
                    kind text not null,
                    enabled integer not null,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists source_items (
                    item_id text primary key,
                    source_id text not null,
                    fingerprint text not null,
                    uri text not null,
                    record_json text not null,
                    collected_at text not null,
                    unique(source_id, fingerprint)
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
