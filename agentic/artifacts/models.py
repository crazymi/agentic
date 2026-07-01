from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def artifact_id() -> str:
    return f"art_{uuid4().hex}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactKind(StrEnum):
    REPORT = "report"
    SCRIPT = "script"
    SCREENSHOT = "screenshot"
    DATASET = "dataset"
    CONFIG = "config"
    LOG = "log"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True)
class ArtifactRecord:
    kind: ArtifactKind
    name: str
    content: str
    artifact_id: str = field(default_factory=artifact_id)
    status: ArtifactStatus = ArtifactStatus.DRAFT
    workflow_id: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", ArtifactKind(self.kind))
        if isinstance(self.status, str):
            object.__setattr__(self, "status", ArtifactStatus(self.status))
        if not self.name:
            raise ValueError("artifact name must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "name": self.name,
            "content": self.content,
            "status": self.status.value,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ArtifactRecord":
        return cls(
            artifact_id=str(record["artifact_id"]),
            kind=ArtifactKind(record["kind"]),
            name=str(record["name"]),
            content=str(record.get("content") or ""),
            status=ArtifactStatus(record.get("status", ArtifactStatus.DRAFT.value)),
            workflow_id=record.get("workflow_id"),
            run_id=record.get("run_id"),
            metadata=dict(record.get("metadata") or {}),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )
