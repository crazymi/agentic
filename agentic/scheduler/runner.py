from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from agentic.scheduler.models import ScheduleRecord
from agentic.scheduler.store import ScheduleStore
from agentic.workflow_kernel.interpreter import WorkflowBuilder, WorkflowExecutionResult
from agentic.workflow_kernel.models import WorkflowStatus, utc_now
from agentic.workflow_kernel.store import WorkflowStore


@dataclass(frozen=True)
class SchedulerRunResult:
    schedule: ScheduleRecord
    workflow_run_id: str
    ok: bool


class SchedulerRunner:
    def __init__(
        self,
        *,
        schedule_store: ScheduleStore,
        workflow_store: WorkflowStore,
        builder: WorkflowBuilder,
    ):
        self.schedule_store = schedule_store
        self.workflow_store = workflow_store
        self.builder = builder

    def run_due_once(self, *, now: str | None = None) -> list[SchedulerRunResult]:
        results: list[SchedulerRunResult] = []
        for schedule in self.schedule_store.list_due(now=now):
            spec = self.workflow_store.get_spec(schedule.workflow_id)
            if spec.status != WorkflowStatus.ACTIVE:
                continue
            execution: WorkflowExecutionResult = self.builder.run_approved(
                spec,
                trigger={"type": "schedule", "schedule_id": schedule.schedule_id},
            )
            last_run_at = utc_now()
            self.schedule_store.mark_run(
                schedule.schedule_id,
                last_run_at=last_run_at,
                next_run_at=_next_run_at(schedule, last_run_at),
            )
            results.append(
                SchedulerRunResult(
                    schedule=schedule,
                    workflow_run_id=execution.run.run_id,
                    ok=execution.ok,
                )
            )
        return results

    def trigger_manual(self, workflow_id: str) -> WorkflowExecutionResult:
        spec = self.workflow_store.get_spec(workflow_id)
        return self.builder.run_approved(spec, trigger={"type": "manual"})


def _next_run_at(schedule: ScheduleRecord, last_run_at: str) -> str | None:
    trigger = schedule.trigger
    if str(trigger.get("type") or "") != "interval":
        return None
    seconds = _interval_seconds(str(trigger.get("value") or trigger.get("interval") or ""))
    if seconds <= 0:
        return None
    base = datetime.fromisoformat(last_run_at)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return (base + timedelta(seconds=seconds)).isoformat()


def _interval_seconds(value: str) -> int:
    match = re.search(r"(\d+)\s*([smhd]?)", value)
    if not match:
        return 0
    amount = int(match.group(1))
    unit = match.group(2) or "s"
    if unit == "m":
        return amount * 60
    if unit == "h":
        return amount * 3600
    if unit == "d":
        return amount * 86400
    return amount
