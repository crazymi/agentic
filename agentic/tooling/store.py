from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.tooling.models import ToolingRequest, ToolingStatus
from agentic.workflow_kernel.models import utc_now


class ToolingBacklogStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(self, request: ToolingRequest) -> ToolingRequest:
        with self._connect() as conn:
            conn.execute(
                """
                insert into tooling_requests (
                    tooling_id, workflow_id, capability, status, record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.tooling_id,
                    request.workflow_id,
                    request.capability,
                    request.status.value,
                    self._dump(request.to_record()),
                    request.created_at,
                    request.updated_at,
                ),
            )
        return request

    def add_many(self, requests: list[ToolingRequest]) -> list[ToolingRequest]:
        return [self.add(request) for request in requests]

    def get(self, tooling_id: str) -> ToolingRequest:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from tooling_requests where tooling_id = ?",
                (tooling_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown tooling request id: {tooling_id}")
        return ToolingRequest.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        workflow_id: str | None = None,
        status: ToolingStatus | str | None = None,
        limit: int = 100,
    ) -> list[ToolingRequest]:
        clauses: list[str] = []
        params: list[Any] = []
        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(ToolingStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from tooling_requests{where} order by updated_at desc limit ?",
                params,
            ).fetchall()
        return [ToolingRequest.from_record(json.loads(row["record_json"])) for row in rows]

    def transition(self, tooling_id: str, status: ToolingStatus | str) -> ToolingRequest:
        current = self.get(tooling_id)
        updated = ToolingRequest.from_record(
            {
                **current.to_record(),
                "status": ToolingStatus(status).value,
                "updated_at": utc_now(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update tooling_requests
                set status = ?, record_json = ?, updated_at = ?
                where tooling_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    tooling_id,
                ),
            )
        return updated

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists tooling_requests (
                    tooling_id text primary key,
                    workflow_id text,
                    capability text not null,
                    status text not null,
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

