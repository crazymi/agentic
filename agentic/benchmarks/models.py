from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentic.workflow_kernel.models import utc_now


class RealBenchmarkStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_EMPTY = "completed_empty"
    NEEDS_CREDENTIAL = "needs_credential"
    NEEDS_INPUT = "needs_input"
    BLOCKED_BY_TOOLING = "blocked_by_tooling"
    FAILED_LIVE_ATTEMPT = "failed_live_attempt"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class RealBenchmarkProbeResult:
    probe_id: str
    title: str
    requirement: str
    status: RealBenchmarkStatus
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    @property
    def ok(self) -> bool:
        return self.status == RealBenchmarkStatus.COMPLETED

    def to_record(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "title": self.title,
            "requirement": self.requirement,
            "status": self.status.value,
            "ok": self.ok,
            "summary": self.summary,
            "evidence": self.evidence,
            "blockers": self.blockers,
            "next_actions": self.next_actions,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass(frozen=True)
class RealBenchmarkResult:
    ok: bool
    state_dir: str
    experience_path: str | None
    probes: list[RealBenchmarkProbeResult]

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "state_dir": self.state_dir,
            "experience_path": self.experience_path,
            "probes": [probe.to_record() for probe in self.probes],
        }
