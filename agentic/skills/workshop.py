from __future__ import annotations

import json
import sqlite3
import textwrap
from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentic.approvals.models import ApprovalRequest, ApprovalStatus
from agentic.approvals.service import ApprovalService
from agentic.skills.loader import SkillLoader
from agentic.skills.models import (
    SkillProposal,
    SkillProposalStatus,
    proposal_hash,
    utc_now,
)


@dataclass(frozen=True)
class SkillProposalReview:
    proposal: SkillProposal
    mode: str
    target_path: Path
    active_exists: bool
    active_text: str
    candidate_text: str
    diff: str
    validation_ok: bool
    active_hash: str
    candidate_hash: str
    diff_hash: str
    review_hash: str
    validation_error: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "proposal": self.proposal.to_record(),
            "mode": self.mode,
            "target_path": str(self.target_path),
            "active_exists": self.active_exists,
            "active_text": self.active_text,
            "candidate_text": self.candidate_text,
            "diff": self.diff,
            "validation_ok": self.validation_ok,
            "active_hash": self.active_hash,
            "candidate_hash": self.candidate_hash,
            "diff_hash": self.diff_hash,
            "review_hash": self.review_hash,
            "validation_error": self.validation_error,
        }


class SkillWorkshopStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, proposal: SkillProposal) -> SkillProposal:
        with self._connect() as conn:
            conn.execute(
                """
                insert into skill_proposals (
                    proposal_id, name, status, target_skill_name, content_hash,
                    record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.name,
                    proposal.status.value,
                    proposal.target_skill_name,
                    proposal.content_hash,
                    json.dumps(proposal.to_record(), ensure_ascii=False, sort_keys=True),
                    proposal.created_at,
                    proposal.updated_at,
                ),
            )
        return proposal

    def get(self, proposal_id: str) -> SkillProposal:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from skill_proposals where proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown skill proposal id: {proposal_id}")
        return SkillProposal.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        status: SkillProposalStatus | str | None = None,
        limit: int = 100,
    ) -> list[SkillProposal]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(SkillProposalStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from skill_proposals{where} order by created_at desc limit ?",
                params,
            ).fetchall()
        return [SkillProposal.from_record(json.loads(row["record_json"])) for row in rows]

    def replace(self, proposal: SkillProposal) -> SkillProposal:
        with self._connect() as conn:
            conn.execute(
                """
                update skill_proposals
                set name = ?, status = ?, target_skill_name = ?, content_hash = ?,
                    record_json = ?, updated_at = ?
                where proposal_id = ?
                """,
                (
                    proposal.name,
                    proposal.status.value,
                    proposal.target_skill_name,
                    proposal.content_hash,
                    json.dumps(proposal.to_record(), ensure_ascii=False, sort_keys=True),
                    proposal.updated_at,
                    proposal.proposal_id,
                ),
            )
        return proposal

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists skill_proposals (
                    proposal_id text primary key,
                    name text not null,
                    status text not null,
                    target_skill_name text not null,
                    content_hash text not null,
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


class SkillWorkshopService:
    def __init__(
        self,
        store: SkillWorkshopStore,
        *,
        skills_root: str | Path = "skills",
    ):
        self.store = store
        self.skills_root = Path(skills_root)

    def propose_create(
        self,
        *,
        name: str,
        description: str,
        proposal_body: str,
        source: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> SkillProposal:
        proposal = SkillProposal(
            name=name,
            description=description,
            proposal_body=proposal_body,
            source=source or "agent",
            metadata=metadata or {},
        )
        target = self.skills_root / proposal.target_skill_name / "SKILL.md"
        if target.exists():
            raise ValueError(f"target skill already exists: {proposal.target_skill_name}")
        return self.store.create(proposal)

    def propose_revision(
        self,
        *,
        name: str,
        description: str,
        proposal_body: str,
        source: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> SkillProposal:
        proposal = SkillProposal(
            name=name,
            description=description,
            proposal_body=proposal_body,
            source=source or "agent",
            metadata={**(metadata or {}), "proposal_kind": "revision"},
        )
        target = self.skills_root / proposal.target_skill_name / "SKILL.md"
        if not target.exists():
            raise ValueError(f"target skill does not exist for revision: {proposal.target_skill_name}")
        return self.store.create(proposal)

    def inspect(self, proposal_id: str) -> SkillProposal:
        return self.store.get(proposal_id)

    def review(self, proposal_id: str) -> SkillProposalReview:
        proposal = self.store.get(proposal_id)
        target = self.skills_root / proposal.target_skill_name / "SKILL.md"
        active_text = target.read_text(encoding="utf-8") if target.exists() else ""
        try:
            candidate_text = self._build_skill_text(proposal)
            validation_ok = True
            validation_error = ""
        except Exception as exc:
            candidate_text = ""
            validation_ok = False
            validation_error = f"{exc.__class__.__name__}: {exc}"
        diff = _unified_text_diff(
            active_text,
            candidate_text,
            fromfile=str(target) if target.exists() else "/dev/null",
            tofile=f"proposal:{proposal.proposal_id}",
        )
        active_hash = _text_hash(active_text)
        candidate_hash = _text_hash(candidate_text)
        diff_hash = _text_hash(diff)
        review_hash = _review_hash(
            proposal=proposal,
            target=target,
            active_hash=active_hash,
            candidate_hash=candidate_hash,
            diff_hash=diff_hash,
            validation_ok=validation_ok,
        )
        return SkillProposalReview(
            proposal=proposal,
            mode="revision" if target.exists() else "create",
            target_path=target,
            active_exists=target.exists(),
            active_text=active_text,
            candidate_text=candidate_text,
            diff=diff,
            validation_ok=validation_ok,
            active_hash=active_hash,
            candidate_hash=candidate_hash,
            diff_hash=diff_hash,
            review_hash=review_hash,
            validation_error=validation_error,
        )

    def list(
        self,
        *,
        status: SkillProposalStatus | str | None = None,
        limit: int = 100,
    ) -> list[SkillProposal]:
        return self.store.list(status=status, limit=limit)

    def revise(
        self,
        proposal_id: str,
        *,
        proposal_body: str,
        reason: str = "",
    ) -> SkillProposal:
        current = self.store.get(proposal_id)
        if current.status != SkillProposalStatus.PENDING:
            raise ValueError(f"only pending proposals can be revised: {current.status.value}")
        updated = SkillProposal.from_record(
            {
                **current.to_record(),
                "proposal_body": proposal_body,
                "reason": reason,
                "content_hash": proposal_hash(proposal_body),
                "updated_at": utc_now(),
            }
        )
        return self.store.replace(updated)

    def reject(self, proposal_id: str, *, reason: str = "") -> SkillProposal:
        return self._transition(proposal_id, SkillProposalStatus.REJECTED, reason=reason)

    def quarantine(self, proposal_id: str, *, reason: str = "") -> SkillProposal:
        return self._transition(proposal_id, SkillProposalStatus.QUARANTINED, reason=reason)

    def request_apply(
        self,
        proposal_id: str,
        *,
        approvals: ApprovalService,
        reason: str = "",
    ) -> ApprovalRequest:
        proposal = self.store.get(proposal_id)
        if proposal.status != SkillProposalStatus.PENDING:
            raise ValueError(f"only pending proposals can request apply: {proposal.status.value}")
        review = self.review(proposal_id)
        if not review.validation_ok:
            raise ValueError(f"proposal review failed: {review.validation_error}")
        return approvals.create_request(
            capability="skill:apply",
            reason=reason or f"Apply pending skill proposal {proposal.target_skill_name}",
            payload={
                "proposal_id": proposal.proposal_id,
                "target_skill_name": proposal.target_skill_name,
                "content_hash": proposal.content_hash,
                "active_hash": review.active_hash,
                "candidate_hash": review.candidate_hash,
                "diff_hash": review.diff_hash,
                "review_hash": review.review_hash,
            },
        )

    def apply(
        self,
        proposal_id: str,
        *,
        approval: ApprovalRequest,
        reason: str = "",
    ) -> SkillProposal:
        proposal = self.store.get(proposal_id)
        if proposal.status != SkillProposalStatus.PENDING:
            raise ValueError(f"only pending proposals can be applied: {proposal.status.value}")
        self._assert_matching_approval(proposal, approval)
        skill_text = self._build_skill_text(proposal)
        target = self.skills_root / proposal.target_skill_name / "SKILL.md"
        is_revision = proposal.metadata.get("proposal_kind") == "revision"
        if target.exists() and not is_revision:
            raise ValueError(f"target skill already exists: {proposal.target_skill_name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(skill_text, encoding="utf-8")
        updated = SkillProposal.from_record(
            {
                **proposal.to_record(),
                "status": SkillProposalStatus.APPLIED.value,
                "reason": reason or f"applied with approval {approval.approval_id}",
                "metadata": {
                    **proposal.metadata,
                    "applied_path": str(target),
                    "approval_id": approval.approval_id,
                },
                "updated_at": utc_now(),
            }
        )
        return self.store.replace(updated)

    def _transition(
        self,
        proposal_id: str,
        status: SkillProposalStatus,
        *,
        reason: str = "",
    ) -> SkillProposal:
        current = self.store.get(proposal_id)
        if current.status != SkillProposalStatus.PENDING:
            raise ValueError(f"only pending proposals can transition: {current.status.value}")
        updated = SkillProposal.from_record(
            {
                **current.to_record(),
                "status": status.value,
                "reason": reason,
                "updated_at": utc_now(),
            }
        )
        return self.store.replace(updated)

    def _assert_matching_approval(
        self,
        proposal: SkillProposal,
        approval: ApprovalRequest,
    ) -> None:
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError(f"approval must be approved: {approval.status.value}")
        if approval.capability != "skill:apply":
            raise ValueError(f"approval capability mismatch: {approval.capability}")
        payload = approval.payload
        if payload.get("proposal_id") != proposal.proposal_id:
            raise ValueError("approval proposal_id does not match")
        if payload.get("target_skill_name") != proposal.target_skill_name:
            raise ValueError("approval target_skill_name does not match")
        if payload.get("content_hash") != proposal.content_hash:
            raise ValueError("approval content_hash does not match current proposal")
        review = self.review(proposal.proposal_id)
        if not review.validation_ok:
            raise ValueError(f"proposal review failed: {review.validation_error}")
        if payload.get("active_hash") != review.active_hash:
            raise ValueError("approval active_hash does not match current active skill")
        if payload.get("candidate_hash") != review.candidate_hash:
            raise ValueError("approval candidate_hash does not match current candidate")
        if payload.get("diff_hash") != review.diff_hash:
            raise ValueError("approval diff_hash does not match current review")
        if payload.get("review_hash") != review.review_hash:
            raise ValueError("approval review_hash does not match current review")

    def _build_skill_text(self, proposal: SkillProposal) -> str:
        body = _normalize_markdown_body(proposal.proposal_body)
        if body.startswith("---\n"):
            skill_text = body.rstrip() + "\n"
        else:
            keywords = _infer_trigger_keywords(proposal)
            skill_text = (
                "---\n"
                f"name: {_yaml_scalar(proposal.target_skill_name)}\n"
                f"description: {_yaml_scalar(proposal.description)}\n"
                "requires:\n"
                "  connectors: []\n"
                "  tools: []\n"
                "  resources: []\n"
                "triggers:\n"
                f"  keywords: {_json_list(keywords)}\n"
                f"  task_kinds: {_json_list([proposal.target_skill_name.replace('-', '_')])}\n"
                "enabled: true\n"
                "---\n\n"
                f"{body}\n"
            )
        loaded = SkillLoader(self.skills_root).load_text(
            skill_text,
            path=self.skills_root / proposal.target_skill_name,
        )
        if loaded.manifest.name != proposal.target_skill_name:
            raise ValueError(
                "skill manifest name must match proposal target skill name: "
                f"{loaded.manifest.name} != {proposal.target_skill_name}"
            )
        return skill_text


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _normalize_markdown_body(value: str) -> str:
    body = textwrap.dedent(value).strip()
    lines = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            lines.append(stripped)
        else:
            lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _infer_trigger_keywords(proposal: SkillProposal) -> list[str]:
    text = f"{proposal.name} {proposal.description} {proposal.proposal_body}".lower()
    keywords = set(proposal.name.split("-"))
    for token in ("workflow", "automation", "automate", "agent", "skill"):
        if token in text:
            keywords.add(token)
    if "workflow" in text:
        keywords.add("워크플로우")
    if "automation" in text or "automate" in text:
        keywords.add("자동화")
    if "proposal" in text:
        keywords.add("제안")
    return sorted(keyword for keyword in keywords if len(keyword) >= 2)


def _unified_text_diff(
    old: str,
    new: str,
    *,
    fromfile: str,
    tofile: str,
) -> str:
    return "".join(
        unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def _text_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _review_hash(
    *,
    proposal: SkillProposal,
    target: Path,
    active_hash: str,
    candidate_hash: str,
    diff_hash: str,
    validation_ok: bool,
) -> str:
    payload = {
        "proposal_id": proposal.proposal_id,
        "target_skill_name": proposal.target_skill_name,
        "content_hash": proposal.content_hash,
        "target_path": str(target),
        "active_hash": active_hash,
        "candidate_hash": candidate_hash,
        "diff_hash": diff_hash,
        "validation_ok": validation_ok,
    }
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
