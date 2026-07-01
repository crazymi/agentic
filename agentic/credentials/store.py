from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agentic.credentials.models import CredentialRef


class CredentialStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(self, credential: CredentialRef) -> CredentialRef:
        with self._connect() as conn:
            conn.execute(
                """
                insert into credential_refs (
                    credential_id, provider, kind, record_json, created_at
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    credential.credential_id,
                    credential.provider,
                    credential.kind.value,
                    json.dumps(credential.to_record(), ensure_ascii=False, sort_keys=True),
                    credential.created_at,
                ),
            )
        return credential

    def get(self, credential_id: str) -> CredentialRef:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from credential_refs where credential_id = ?",
                (credential_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown credential ref id: {credential_id}")
        return CredentialRef.from_record(json.loads(row["record_json"]))

    def list(self, *, provider: str | None = None, limit: int = 100) -> list[CredentialRef]:
        params: list[object] = []
        where = ""
        if provider is not None:
            where = " where provider = ?"
            params.append(provider)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from credential_refs{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [CredentialRef.from_record(json.loads(row["record_json"])) for row in rows]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists credential_refs (
                    credential_id text primary key,
                    provider text not null,
                    kind text not null,
                    record_json text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
