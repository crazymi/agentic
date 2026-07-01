from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.workflow_kernel.models import WorkflowDesignSession


class PlanningSessionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def upsert(self, session: WorkflowDesignSession) -> WorkflowDesignSession:
        with self._connect() as conn:
            conn.execute(
                """
                insert into workflow_design_sessions (
                    session_id, status, proposed_workflow_id, record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(session_id) do update set
                    status = excluded.status,
                    proposed_workflow_id = excluded.proposed_workflow_id,
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session.session_id,
                    session.status,
                    session.proposed_workflow_id,
                    self._dump(session.to_record()),
                    session.created_at,
                    session.updated_at,
                ),
            )
        return session

    def get(self, session_id: str) -> WorkflowDesignSession:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from workflow_design_sessions where session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown planning session id: {session_id}")
        return WorkflowDesignSession.from_record(json.loads(row["record_json"]))

    def list(self, *, status: str | None = None, limit: int = 100) -> list[WorkflowDesignSession]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from workflow_design_sessions{where} order by updated_at desc limit ?",
                params,
            ).fetchall()
        return [WorkflowDesignSession.from_record(json.loads(row["record_json"])) for row in rows]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists workflow_design_sessions (
                    session_id text primary key,
                    status text not null,
                    proposed_workflow_id text,
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

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

