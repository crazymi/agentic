from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.tasks.state_machine import (
    DurableTaskStatus,
    TERMINAL_STATUSES,
    TaskRecord,
    assert_transition,
    utc_now,
)


class TaskStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_task(
        self,
        *,
        kind: str,
        input: dict[str, Any],
        task_id: str | None = None,
    ) -> TaskRecord:
        record = TaskRecord(kind=kind, input=input, task_id=task_id) if task_id else TaskRecord(kind=kind, input=input)
        with self._connect() as conn:
            conn.execute(
                """
                insert into tasks (
                    task_id, kind, status, input_json, result_json, error_json,
                    created_at, updated_at, started_at, completed_at, last_heartbeat_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._row_values(record),
            )
            conn.execute(
                "insert into task_events (task_id, event_type, payload_json, created_at) values (?, ?, ?, ?)",
                (
                    record.task_id,
                    "task_created",
                    json.dumps({"status": record.status.value}, ensure_ascii=False),
                    utc_now(),
                ),
            )
        return record

    def get_task(self, task_id: str) -> TaskRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select * from tasks where task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown durable task id: {task_id}")
        return self._record_from_row(row)

    def list_tasks(
        self,
        *,
        status: DurableTaskStatus | str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[TaskRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(DurableTaskStatus(status).value)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select * from tasks{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def transition(
        self,
        task_id: str,
        status: DurableTaskStatus | str,
        *,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        event_type: str = "task_state_changed",
        event_payload: dict[str, Any] | None = None,
    ) -> TaskRecord:
        next_status = DurableTaskStatus(status)
        current = self.get_task(task_id)
        assert_transition(current.status, next_status)
        now = utc_now()
        started_at = current.started_at
        completed_at = current.completed_at
        last_heartbeat_at = current.last_heartbeat_at
        if next_status == DurableTaskStatus.RUNNING and started_at is None:
            started_at = now
            last_heartbeat_at = now
        if next_status in TERMINAL_STATUSES and completed_at is None:
            completed_at = now
        updated = TaskRecord(
            task_id=current.task_id,
            kind=current.kind,
            input=current.input,
            status=next_status,
            result=result if result is not None else current.result,
            error=error if error is not None else current.error,
            created_at=current.created_at,
            updated_at=now,
            started_at=started_at,
            completed_at=completed_at,
            last_heartbeat_at=last_heartbeat_at,
        )
        with self._connect() as conn:
            conn.execute(
                """
                update tasks
                set status = ?, result_json = ?, error_json = ?, updated_at = ?,
                    started_at = ?, completed_at = ?, last_heartbeat_at = ?
                where task_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.result),
                    self._dump(updated.error),
                    updated.updated_at,
                    updated.started_at,
                    updated.completed_at,
                    updated.last_heartbeat_at,
                    updated.task_id,
                ),
            )
            self._append_event_conn(
                conn,
                task_id,
                event_type,
                event_payload
                or {"from": current.status.value, "to": updated.status.value},
            )
        return updated

    def claim_next(self) -> TaskRecord | None:
        with self._connect() as conn:
            conn.execute("begin immediate")
            row = conn.execute(
                """
                select * from tasks
                where status = ?
                order by created_at asc
                limit 1
                """,
                (DurableTaskStatus.QUEUED.value,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            current = self._record_from_row(row)
            now = utc_now()
            conn.execute(
                """
                update tasks
                set status = ?, updated_at = ?, started_at = ?, last_heartbeat_at = ?
                where task_id = ? and status = ?
                """,
                (
                    DurableTaskStatus.RUNNING.value,
                    now,
                    now,
                    now,
                    current.task_id,
                    DurableTaskStatus.QUEUED.value,
                ),
            )
            self._append_event_conn(
                conn,
                current.task_id,
                "task_started",
                {"from": current.status.value, "to": DurableTaskStatus.RUNNING.value},
            )
            conn.commit()
        return self.get_task(current.task_id)

    def heartbeat(self, task_id: str) -> TaskRecord:
        current = self.get_task(task_id)
        if current.status not in {
            DurableTaskStatus.RUNNING,
            DurableTaskStatus.CANCEL_REQUESTED,
        }:
            raise ValueError(f"cannot heartbeat task in status {current.status}")
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                "update tasks set last_heartbeat_at = ?, updated_at = ? where task_id = ?",
                (now, now, task_id),
            )
            self._append_event_conn(conn, task_id, "task_heartbeat", {"at": now})
        return self.get_task(task_id)

    def append_event(
        self,
        task_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            self._append_event_conn(conn, task_id, event_type, payload or {})

    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select event_type, payload_json, created_at
                from task_events
                where task_id = ?
                order by id asc
                """,
                (task_id,),
            ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists tasks (
                    task_id text primary key,
                    kind text not null,
                    status text not null,
                    input_json text not null,
                    result_json text,
                    error_json text,
                    created_at text not null,
                    updated_at text not null,
                    started_at text,
                    completed_at text,
                    last_heartbeat_at text
                )
                """
            )
            conn.execute(
                """
                create table if not exists task_events (
                    id integer primary key autoincrement,
                    task_id text not null,
                    event_type text not null,
                    payload_json text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_values(self, record: TaskRecord) -> tuple[Any, ...]:
        return (
            record.task_id,
            record.kind,
            record.status.value,
            self._dump(record.input),
            self._dump(record.result),
            self._dump(record.error),
            record.created_at,
            record.updated_at,
            record.started_at,
            record.completed_at,
            record.last_heartbeat_at,
        )

    def _record_from_row(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            kind=row["kind"],
            status=DurableTaskStatus(row["status"]),
            input=json.loads(row["input_json"]),
            result=self._load(row["result_json"]),
            error=self._load(row["error_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            last_heartbeat_at=row["last_heartbeat_at"],
        )

    def _append_event_conn(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        conn.execute(
            "insert into task_events (task_id, event_type, payload_json, created_at) values (?, ?, ?, ?)",
            (task_id, event_type, self._dump(payload), utc_now()),
        )

    def _dump(self, value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def _load(self, value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)
