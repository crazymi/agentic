from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic.artifacts.models import ArtifactKind, ArtifactRecord, ArtifactStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, artifact: ArtifactRecord) -> ArtifactRecord:
        with self._connect() as conn:
            conn.execute(
                """
                insert into artifacts (
                    artifact_id, kind, status, workflow_id, run_id, record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id,
                    artifact.kind.value,
                    artifact.status.value,
                    artifact.workflow_id,
                    artifact.run_id,
                    json.dumps(artifact.to_record(), ensure_ascii=False, sort_keys=True),
                    artifact.created_at,
                    artifact.updated_at,
                ),
            )
        return artifact

    def get(self, artifact_id: str) -> ArtifactRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from artifacts where artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown artifact id: {artifact_id}")
        return ArtifactRecord.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        workflow_id: str | None = None,
        run_id: str | None = None,
        kind: ArtifactKind | str | None = None,
        status: ArtifactStatus | str | None = None,
        limit: int = 100,
    ) -> list[ArtifactRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(ArtifactKind(kind).value)
        if status is not None:
            clauses.append("status = ?")
            params.append(ArtifactStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from artifacts{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [ArtifactRecord.from_record(json.loads(row["record_json"])) for row in rows]

    def transition(self, artifact_id: str, status: ArtifactStatus | str) -> ArtifactRecord:
        current = self.get(artifact_id)
        next_status = ArtifactStatus(status)
        updated = ArtifactRecord.from_record(
            {
                **current.to_record(),
                "status": next_status.value,
                "updated_at": utc_now(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                "update artifacts set status = ?, record_json = ?, updated_at = ? where artifact_id = ?",
                (
                    updated.status.value,
                    json.dumps(updated.to_record(), ensure_ascii=False, sort_keys=True),
                    updated.updated_at,
                    artifact_id,
                ),
            )
        return updated

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists artifacts (
                    artifact_id text primary key,
                    kind text not null,
                    status text not null,
                    workflow_id text,
                    run_id text,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
