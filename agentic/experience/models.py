from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from agentic.workflow_kernel.models import utc_now


def experience_event_id() -> str:
    return f"exp_{uuid4().hex}"


class ExperienceEventType(StrEnum):
    REQUIREMENT_PROBE = "requirement_probe"
    SMOKE_RUN = "smoke_run"
    DECISION = "decision"
    LESSON = "lesson"
    BOTTLENECK = "bottleneck"


@dataclass(frozen=True)
class ExperienceEvent:
    event_type: ExperienceEventType
    subject: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    event_id: str = field(default_factory=experience_event_id)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.event_type, str):
            object.__setattr__(self, "event_type", ExperienceEventType(self.event_type))
        if not self.subject:
            raise ValueError("subject must not be empty")
        if not self.summary:
            raise ValueError("summary must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "subject": self.subject,
            "summary": self.summary,
            "evidence": self.evidence,
            "lessons": self.lessons,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ExperienceEvent":
        return cls(
            event_id=str(record["event_id"]),
            event_type=ExperienceEventType(record["event_type"]),
            subject=str(record["subject"]),
            summary=str(record["summary"]),
            evidence=dict(record.get("evidence") or {}),
            lessons=list(record.get("lessons") or []),
            tags=list(record.get("tags") or []),
            created_at=str(record.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class RequirementProbe:
    probe_id: str
    title: str
    request: str
    expected_pattern: str
    continuation_answer: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RequirementProbeResult:
    probe: RequirementProbe
    level: str
    ok: bool
    intent: str
    status: str
    workflow_id: str | None
    run_id: str | None
    bottlenecks: list[str]
    tooling_requests: list[dict[str, Any]]
    lessons: list[str]

    def to_record(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe.probe_id,
            "title": self.probe.title,
            "request": self.probe.request,
            "expected_pattern": self.probe.expected_pattern,
            "level": self.level,
            "ok": self.ok,
            "intent": self.intent,
            "status": self.status,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "bottlenecks": self.bottlenecks,
            "tooling_requests": self.tooling_requests,
            "lessons": self.lessons,
            "tags": self.probe.tags,
        }


@dataclass(frozen=True)
class RequirementSmokeResult:
    ok: bool
    state_dir: str
    experience_path: str | None
    results: list[RequirementProbeResult]

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "state_dir": self.state_dir,
            "experience_path": self.experience_path,
            "results": [result.to_record() for result in self.results],
        }

