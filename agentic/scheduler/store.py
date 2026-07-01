from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.scheduler.models import ScheduleRecord, ScheduleStatus
from agentic.workflow_kernel.models import utc_now


class ScheduleStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, schedule: ScheduleRecord) -> ScheduleRecord:
        with self._connect() as conn:
            conn.execute(
                """
                insert into schedules (
                    schedule_id, workflow_id, status, trigger_json, record_json,
                    last_run_at, next_run_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule.schedule_id,
                    schedule.workflow_id,
                    schedule.status.value,
                    json.dumps(schedule.trigger, ensure_ascii=False, sort_keys=True),
                    json.dumps(schedule.to_record(), ensure_ascii=False, sort_keys=True),
                    schedule.last_run_at,
                    schedule.next_run_at,
                    schedule.created_at,
                    schedule.updated_at,
                ),
            )
        return schedule

    def list_due(self, *, now: str | None = None, limit: int = 100) -> list[ScheduleRecord]:
        current = now or utc_now()
        with self._connect() as conn:
            rows = conn.execute(
                """
                select record_json from schedules
                where status = ? and (next_run_at is null or next_run_at <= ?)
                order by created_at asc
                limit ?
                """,
                (ScheduleStatus.ACTIVE.value, current, limit),
            ).fetchall()
        return [ScheduleRecord.from_record(json.loads(row["record_json"])) for row in rows]

    def mark_run(self, schedule_id: str, *, last_run_at: str | None = None, next_run_at: str | None = None) -> ScheduleRecord:
        current = self.get(schedule_id)
        updated = ScheduleRecord.from_record(
            {
                **current.to_record(),
                "last_run_at": last_run_at or utc_now(),
                "next_run_at": next_run_at,
                "updated_at": utc_now(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update schedules
                set record_json = ?, last_run_at = ?, next_run_at = ?, updated_at = ?
                where schedule_id = ?
                """,
                (
                    json.dumps(updated.to_record(), ensure_ascii=False, sort_keys=True),
                    updated.last_run_at,
                    updated.next_run_at,
                    updated.updated_at,
                    schedule_id,
                ),
            )
        return updated

    def pause(self, schedule_id: str) -> ScheduleRecord:
        return self._status(schedule_id, ScheduleStatus.PAUSED)

    def resume(self, schedule_id: str) -> ScheduleRecord:
        return self._status(schedule_id, ScheduleStatus.ACTIVE)

    def get(self, schedule_id: str) -> ScheduleRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from schedules where schedule_id = ?",
                (schedule_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown schedule id: {schedule_id}")
        return ScheduleRecord.from_record(json.loads(row["record_json"]))

    def _status(self, schedule_id: str, status: ScheduleStatus) -> ScheduleRecord:
        current = self.get(schedule_id)
        updated = ScheduleRecord.from_record(
            {**current.to_record(), "status": status.value, "updated_at": utc_now()}
        )
        with self._connect() as conn:
            conn.execute(
                "update schedules set status = ?, record_json = ?, updated_at = ? where schedule_id = ?",
                (
                    updated.status.value,
                    json.dumps(updated.to_record(), ensure_ascii=False, sort_keys=True),
                    updated.updated_at,
                    schedule_id,
                ),
            )
        return updated

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists schedules (
                    schedule_id text primary key,
                    workflow_id text not null,
                    status text not null,
                    trigger_json text not null,
                    record_json text not null,
                    last_run_at text,
                    next_run_at text,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
