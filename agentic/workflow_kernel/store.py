from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.workflow_kernel.models import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowSpec,
    WorkflowStatus,
    assert_run_transition,
    assert_workflow_transition,
    utc_now,
)


class WorkflowStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_spec(self, spec: WorkflowSpec) -> WorkflowSpec:
        with self._connect() as conn:
            conn.execute(
                """
                insert into workflow_specs (
                    workflow_id, version, status, record_json, created_at, updated_at, approved_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spec.workflow_id,
                    spec.version,
                    spec.status.value,
                    self._dump(spec.to_record()),
                    spec.created_at,
                    spec.updated_at,
                    spec.approved_at,
                ),
            )
            self._append_event_conn(
                conn,
                "workflow_created",
                {"workflow_id": spec.workflow_id, "status": spec.status.value},
                workflow_id=spec.workflow_id,
            )
        return spec

    def get_spec(self, workflow_id: str) -> WorkflowSpec:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from workflow_specs where workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown workflow id: {workflow_id}")
        return WorkflowSpec.from_record(json.loads(row["record_json"]))

    def update_spec(
        self,
        spec: WorkflowSpec,
        *,
        event_type: str = "workflow_updated",
        event_payload: dict[str, Any] | None = None,
    ) -> WorkflowSpec:
        current = self.get_spec(spec.workflow_id)
        if current.version != spec.version:
            raise ValueError("workflow version mismatch")
        now = utc_now()
        updated = WorkflowSpec.from_record({**spec.to_record(), "updated_at": now})
        with self._connect() as conn:
            conn.execute(
                """
                update workflow_specs
                set status = ?, record_json = ?, updated_at = ?, approved_at = ?
                where workflow_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    updated.approved_at,
                    updated.workflow_id,
                ),
            )
            self._append_event_conn(
                conn,
                event_type,
                event_payload or {"workflow_id": updated.workflow_id},
                workflow_id=updated.workflow_id,
            )
        return updated

    def list_specs(
        self,
        *,
        status: WorkflowStatus | str | None = None,
        limit: int = 100,
    ) -> list[WorkflowSpec]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(WorkflowStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from workflow_specs{where} order by updated_at desc limit ?",
                params,
            ).fetchall()
        return [WorkflowSpec.from_record(json.loads(row["record_json"])) for row in rows]

    def transition_spec(
        self,
        workflow_id: str,
        status: WorkflowStatus | str,
        *,
        event_type: str = "workflow_state_changed",
        event_payload: dict[str, Any] | None = None,
    ) -> WorkflowSpec:
        next_status = WorkflowStatus(status)
        current = self.get_spec(workflow_id)
        assert_workflow_transition(current.status, next_status)
        if next_status == WorkflowStatus.ACTIVE and current.status != WorkflowStatus.APPROVED:
            raise ValueError("workflow must be approved before activation")
        now = utc_now()
        approved_at = current.approved_at
        if next_status == WorkflowStatus.APPROVED and approved_at is None:
            approved_at = now
        updated = WorkflowSpec.from_record(
            {
                **current.to_record(),
                "status": next_status.value,
                "updated_at": now,
                "approved_at": approved_at,
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update workflow_specs
                set status = ?, record_json = ?, updated_at = ?, approved_at = ?
                where workflow_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    updated.approved_at,
                    workflow_id,
                ),
            )
            self._append_event_conn(
                conn,
                event_type,
                event_payload
                or {"from": current.status.value, "to": updated.status.value},
                workflow_id=workflow_id,
            )
        return updated

    def create_run(
        self,
        spec: WorkflowSpec,
        *,
        trigger: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=spec.workflow_id,
            workflow_version=spec.version,
            trigger=trigger or {},
            context=context or {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                insert into workflow_runs (
                    run_id, workflow_id, workflow_version, status, record_json,
                    created_at, updated_at, started_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.workflow_id,
                    run.workflow_version,
                    run.status.value,
                    self._dump(run.to_record()),
                    run.created_at,
                    run.updated_at,
                    run.started_at,
                    run.completed_at,
                ),
            )
            self._append_event_conn(
                conn,
                "workflow_run_created",
                {"run_id": run.run_id, "workflow_id": run.workflow_id},
                workflow_id=run.workflow_id,
                run_id=run.run_id,
            )
        return run

    def get_run(self, run_id: str) -> WorkflowRun:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from workflow_runs where run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown workflow run id: {run_id}")
        return WorkflowRun.from_record(json.loads(row["record_json"]))

    def list_runs(
        self,
        *,
        workflow_id: str | None = None,
        status: WorkflowRunStatus | str | None = None,
        limit: int = 100,
    ) -> list[WorkflowRun]:
        clauses: list[str] = []
        params: list[Any] = []
        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(WorkflowRunStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from workflow_runs{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [WorkflowRun.from_record(json.loads(row["record_json"])) for row in rows]

    def transition_run(
        self,
        run_id: str,
        status: WorkflowRunStatus | str,
        *,
        context: dict[str, Any] | None = None,
        step_results: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        event_type: str = "workflow_run_state_changed",
        event_payload: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        next_status = WorkflowRunStatus(status)
        current = self.get_run(run_id)
        assert_run_transition(current.status, next_status)
        now = utc_now()
        started_at = current.started_at
        completed_at = current.completed_at
        if next_status == WorkflowRunStatus.RUNNING and started_at is None:
            started_at = now
        if next_status in {
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.UNHEALTHY,
        } and completed_at is None:
            completed_at = now
        updated = WorkflowRun.from_record(
            {
                **current.to_record(),
                "status": next_status.value,
                "context": context if context is not None else current.context,
                "step_results": step_results if step_results is not None else current.step_results,
                "artifacts": artifacts if artifacts is not None else current.artifacts,
                "result": result if result is not None else current.result,
                "error": error if error is not None else current.error,
                "updated_at": now,
                "started_at": started_at,
                "completed_at": completed_at,
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update workflow_runs
                set status = ?, record_json = ?, updated_at = ?, started_at = ?, completed_at = ?
                where run_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    updated.started_at,
                    updated.completed_at,
                    run_id,
                ),
            )
            self._append_event_conn(
                conn,
                event_type,
                event_payload or {"from": current.status.value, "to": updated.status.value},
                workflow_id=updated.workflow_id,
                run_id=run_id,
            )
        return updated

    def append_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        workflow_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            self._append_event_conn(
                conn,
                event_type,
                payload,
                workflow_id=workflow_id,
                run_id=run_id,
            )

    def list_events(
        self,
        *,
        workflow_id: str | None = None,
        run_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select workflow_id, run_id, event_type, payload_json, created_at
                from workflow_events{where}
                order by id asc
                limit ?
                """,
                params,
            ).fetchall()
        return [
            {
                "workflow_id": row["workflow_id"],
                "run_id": row["run_id"],
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
                create table if not exists workflow_specs (
                    workflow_id text primary key,
                    version integer not null,
                    status text not null,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null,
                    approved_at text
                )
                """
            )
            conn.execute(
                """
                create table if not exists workflow_runs (
                    run_id text primary key,
                    workflow_id text not null,
                    workflow_version integer not null,
                    status text not null,
                    record_json text not null,
                    created_at text not null,
                    updated_at text not null,
                    started_at text,
                    completed_at text
                )
                """
            )
            conn.execute(
                """
                create table if not exists workflow_events (
                    id integer primary key autoincrement,
                    workflow_id text,
                    run_id text,
                    event_type text not null,
                    payload_json text not null,
                    created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _append_event_conn(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        payload: dict[str, Any],
        *,
        workflow_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        conn.execute(
            """
            insert into workflow_events (workflow_id, run_id, event_type, payload_json, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                run_id,
                event_type,
                self._dump(payload),
                utc_now(),
            ),
        )

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
