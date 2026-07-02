from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from agentic.delivery import DeliveryBatchResult, ReportDeliveryService
from agentic.runtime.heartbeat import Watchdog
from agentic.runtime.task_pool import TaskPool


class DueScheduler(Protocol):
    def run_due_once(self) -> list:
        ...


@dataclass(frozen=True)
class RuntimeTickResult:
    schedules_run: int = 0
    tasks_submitted: int = 0
    pool_idle: bool = True
    delivery: DeliveryBatchResult = field(default_factory=DeliveryBatchResult)
    unhealthy_task_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.pool_idle and self.delivery.ok

    def to_record(self) -> dict:
        return {
            "ok": self.ok,
            "schedules_run": self.schedules_run,
            "tasks_submitted": self.tasks_submitted,
            "pool_idle": self.pool_idle,
            "unhealthy_task_ids": self.unhealthy_task_ids,
            "delivery": self.delivery.to_record(),
        }


class RuntimeTickService:
    def __init__(
        self,
        *,
        task_pool: TaskPool,
        watchdog: Watchdog | None = None,
        report_delivery: ReportDeliveryService | None = None,
        scheduler: DueScheduler | None = None,
    ):
        self.task_pool = task_pool
        self.watchdog = watchdog
        self.report_delivery = report_delivery
        self.scheduler = scheduler

    def run_once(
        self,
        *,
        wait: bool = True,
        timeout_s: float = 120.0,
    ) -> RuntimeTickResult:
        unhealthy_task_ids: list[str] = []
        if self.watchdog is not None:
            unhealthy_task_ids = self.watchdog.mark_stale_tasks_unhealthy()

        schedules_run = 0
        if self.scheduler is not None:
            schedules_run = len(self.scheduler.run_due_once())

        tasks_submitted = self.task_pool.kick()
        pool_idle = True
        if wait:
            pool_idle = self._wait_for_idle(timeout_s=timeout_s)

        delivery = DeliveryBatchResult()
        if self.report_delivery is not None:
            delivery = self.report_delivery.enqueue_and_deliver_reports()

        return RuntimeTickResult(
            schedules_run=schedules_run,
            tasks_submitted=tasks_submitted,
            pool_idle=pool_idle,
            delivery=delivery,
            unhealthy_task_ids=unhealthy_task_ids,
        )

    def _wait_for_idle(self, *, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.task_pool.running_count() == 0:
                return True
            time.sleep(0.25)
        return False
