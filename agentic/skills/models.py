from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def skill_proposal_id() -> str:
    return f"skp_{uuid4().hex}"


@dataclass(frozen=True)
class SkillRequirements:
    connectors: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillTriggers:
    keywords: list[str] = field(default_factory=list)
    task_kinds: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    requires: SkillRequirements = field(default_factory=SkillRequirements)
    triggers: SkillTriggers = field(default_factory=SkillTriggers)
    enabled: bool = True


@dataclass(frozen=True)
class SkillPackage:
    path: Path
    manifest: SkillManifest
    body: str

    @property
    def name(self) -> str:
        return self.manifest.name


class SkillProposalStatus(StrEnum):
    PENDING = "pending"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    APPLIED = "applied"
    STALE = "stale"


@dataclass(frozen=True)
class SkillProposal:
    name: str
    description: str
    proposal_body: str
    proposal_id: str = field(default_factory=skill_proposal_id)
    status: SkillProposalStatus = SkillProposalStatus.PENDING
    source: str = "agent"
    target_skill_name: str = ""
    reason: str = ""
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            object.__setattr__(self, "status", SkillProposalStatus(self.status))
        normalized_name = normalize_skill_name(self.name)
        if normalized_name != self.name:
            object.__setattr__(self, "name", normalized_name)
        if not self.name:
            raise ValueError("skill proposal name must not be empty")
        if not _SKILL_NAME_RE.fullmatch(self.name):
            raise ValueError("skill proposal name must use lowercase letters, digits, and hyphens")
        if len(self.name) > 63:
            raise ValueError("skill proposal name must be shorter than 64 characters")
        if not self.description:
            raise ValueError("skill proposal description must not be empty")
        if len(self.description.encode("utf-8")) > 160:
            raise ValueError("skill proposal description must be 160 bytes or less")
        if not self.proposal_body.strip():
            raise ValueError("skill proposal body must not be empty")
        if len(self.proposal_body.encode("utf-8")) > 40_000:
            raise ValueError("skill proposal body must be 40000 bytes or less")
        if not self.target_skill_name:
            object.__setattr__(self, "target_skill_name", self.name)
        if not self.content_hash:
            object.__setattr__(self, "content_hash", proposal_hash(self.proposal_body))
        _reject_secret_payload(self.metadata)

    def to_record(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "name": self.name,
            "description": self.description,
            "proposal_body": self.proposal_body,
            "status": self.status.value,
            "source": self.source,
            "target_skill_name": self.target_skill_name,
            "reason": self.reason,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SkillProposal":
        return cls(
            proposal_id=str(record["proposal_id"]),
            name=str(record["name"]),
            description=str(record["description"]),
            proposal_body=str(record.get("proposal_body") or ""),
            status=SkillProposalStatus(record.get("status", SkillProposalStatus.PENDING.value)),
            source=str(record.get("source") or "agent"),
            target_skill_name=str(record.get("target_skill_name") or ""),
            reason=str(record.get("reason") or ""),
            content_hash=str(record.get("content_hash") or ""),
            metadata=dict(record.get("metadata") or {}),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
        )


_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def normalize_skill_name(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:63]


def proposal_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _reject_secret_payload(payload: dict[str, Any]) -> None:
    forbidden = {"secret", "token", "password", "credential", "api_key", "apikey", "value"}
    for key in payload:
        lowered = str(key).lower()
        if lowered in forbidden or any(word in lowered for word in forbidden):
            raise ValueError(f"metadata must not contain secret-like key: {key}")
