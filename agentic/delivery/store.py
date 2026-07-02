from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentic.delivery.models import DeliveryChannel, DeliveryRecord, DeliveryStatus, utc_now


class DeliveryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, delivery: DeliveryRecord) -> DeliveryRecord:
        with self._connect() as conn:
            conn.execute(
                """
                insert into deliveries (
                    delivery_id, artifact_id, channel, destination, status, record_json,
                    created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery.delivery_id,
                    delivery.artifact_id,
                    delivery.channel.value,
                    delivery.destination,
                    delivery.status.value,
                    json.dumps(delivery.to_record(), ensure_ascii=False, sort_keys=True),
                    delivery.created_at,
                    delivery.updated_at,
                ),
            )
        return delivery

    def get(self, delivery_id: str) -> DeliveryRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from deliveries where delivery_id = ?",
                (delivery_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown delivery id: {delivery_id}")
        return DeliveryRecord.from_record(json.loads(row["record_json"]))

    def find_by_artifact_channel(
        self,
        artifact_id: str,
        channel: DeliveryChannel | str,
    ) -> DeliveryRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select record_json from deliveries
                where artifact_id = ? and channel = ?
                order by created_at desc
                limit 1
                """,
                (artifact_id, DeliveryChannel(channel).value),
            ).fetchone()
        if row is None:
            return None
        return DeliveryRecord.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        status: DeliveryStatus | str | None = None,
        channel: DeliveryChannel | str | None = None,
        limit: int = 100,
    ) -> list[DeliveryRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(DeliveryStatus(status).value)
        if channel is not None:
            clauses.append("channel = ?")
            params.append(DeliveryChannel(channel).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from deliveries{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [DeliveryRecord.from_record(json.loads(row["record_json"])) for row in rows]

    def mark_sent(self, delivery_id: str) -> DeliveryRecord:
        current = self.get(delivery_id)
        now = utc_now()
        updated = DeliveryRecord.from_record(
            {
                **current.to_record(),
                "status": DeliveryStatus.SENT.value,
                "attempts": current.attempts + 1,
                "error": None,
                "sent_at": now,
                "updated_at": now,
            }
        )
        return self._replace(updated)

    def mark_failed(self, delivery_id: str, error: dict[str, Any]) -> DeliveryRecord:
        current = self.get(delivery_id)
        now = utc_now()
        updated = DeliveryRecord.from_record(
            {
                **current.to_record(),
                "status": DeliveryStatus.FAILED.value,
                "attempts": current.attempts + 1,
                "error": error,
                "updated_at": now,
            }
        )
        return self._replace(updated)

    def _replace(self, delivery: DeliveryRecord) -> DeliveryRecord:
        with self._connect() as conn:
            conn.execute(
                """
                update deliveries
                set status = ?, record_json = ?, updated_at = ?
                where delivery_id = ?
                """,
                (
                    delivery.status.value,
                    json.dumps(delivery.to_record(), ensure_ascii=False, sort_keys=True),
                    delivery.updated_at,
                    delivery.delivery_id,
                ),
            )
        return delivery

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists deliveries (
                    delivery_id text primary key,
                    artifact_id text not null,
                    channel text not null,
                    destination text,
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
