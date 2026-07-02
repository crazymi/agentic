from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from agentic.sources.models import SourceDefinition, SourceKind, utc_now
from agentic.sources.quality import NAVIGATION_TERMS
from agentic.sources.store import SourceStore


def source_strategy_proposal_id() -> str:
    return f"ssprop_{uuid4().hex}"


class SourceStrategyProposalStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


@dataclass(frozen=True)
class SourceStrategyProposal:
    source_id: str
    workflow_id: str | None
    run_id: str
    tooling_id: str
    current_metadata: dict[str, Any]
    proposed_metadata: dict[str, Any]
    rationale: str
    quality_reports: list[dict[str, Any]] = field(default_factory=list)
    candidate_actions: list[str] = field(default_factory=list)
    proposal_id: str = field(default_factory=source_strategy_proposal_id)
    status: SourceStrategyProposalStatus = SourceStrategyProposalStatus.PENDING
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    applied_at: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        if not self.tooling_id:
            raise ValueError("tooling_id must not be empty")
        if isinstance(self.status, str):
            object.__setattr__(self, "status", SourceStrategyProposalStatus(self.status))

    def to_record(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "source_id": self.source_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "tooling_id": self.tooling_id,
            "status": self.status.value,
            "current_metadata": self.current_metadata,
            "proposed_metadata": self.proposed_metadata,
            "rationale": self.rationale,
            "quality_reports": self.quality_reports,
            "candidate_actions": self.candidate_actions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "applied_at": self.applied_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SourceStrategyProposal":
        return cls(
            proposal_id=str(record["proposal_id"]),
            source_id=str(record["source_id"]),
            workflow_id=record.get("workflow_id"),
            run_id=str(record.get("run_id") or ""),
            tooling_id=str(record["tooling_id"]),
            status=SourceStrategyProposalStatus(record.get("status", "pending")),
            current_metadata=dict(record.get("current_metadata") or {}),
            proposed_metadata=dict(record.get("proposed_metadata") or {}),
            rationale=str(record.get("rationale") or ""),
            quality_reports=list(record.get("quality_reports") or []),
            candidate_actions=list(record.get("candidate_actions") or []),
            created_at=str(record.get("created_at") or utc_now()),
            updated_at=str(record.get("updated_at") or utc_now()),
            applied_at=record.get("applied_at"),
        )


class SourceStrategyProposalStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(self, proposal: SourceStrategyProposal) -> SourceStrategyProposal:
        with self._connect() as conn:
            conn.execute(
                """
                insert into source_strategy_proposals (
                    proposal_id, source_id, workflow_id, tooling_id, status,
                    record_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.source_id,
                    proposal.workflow_id,
                    proposal.tooling_id,
                    proposal.status.value,
                    self._dump(proposal.to_record()),
                    proposal.created_at,
                    proposal.updated_at,
                ),
            )
        return proposal

    def get(self, proposal_id: str) -> SourceStrategyProposal:
        with self._connect() as conn:
            row = conn.execute(
                "select record_json from source_strategy_proposals where proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown source strategy proposal id: {proposal_id}")
        return SourceStrategyProposal.from_record(json.loads(row["record_json"]))

    def list(
        self,
        *,
        source_id: str | None = None,
        status: SourceStrategyProposalStatus | str | None = None,
        limit: int = 100,
    ) -> list[SourceStrategyProposal]:
        clauses: list[str] = []
        params: list[Any] = []
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(SourceStrategyProposalStatus(status).value)
        where = f" where {' and '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"select record_json from source_strategy_proposals{where} order by updated_at desc limit ?",
                params,
            ).fetchall()
        return [SourceStrategyProposal.from_record(json.loads(row["record_json"])) for row in rows]

    def find_by_tooling(
        self,
        tooling_id: str,
        *,
        status: SourceStrategyProposalStatus | str | None = None,
    ) -> SourceStrategyProposal | None:
        clauses = ["tooling_id = ?"]
        params: list[Any] = [tooling_id]
        if status is not None:
            clauses.append("status = ?")
            params.append(SourceStrategyProposalStatus(status).value)
        with self._connect() as conn:
            row = conn.execute(
                f"select record_json from source_strategy_proposals where {' and '.join(clauses)} order by updated_at desc limit 1",
                params,
            ).fetchone()
        if row is None:
            return None
        return SourceStrategyProposal.from_record(json.loads(row["record_json"]))

    def transition(
        self,
        proposal_id: str,
        status: SourceStrategyProposalStatus | str,
    ) -> SourceStrategyProposal:
        current = self.get(proposal_id)
        next_status = SourceStrategyProposalStatus(status)
        if current.status != SourceStrategyProposalStatus.PENDING:
            raise ValueError(f"source strategy proposal is not pending: {proposal_id}")
        updated = SourceStrategyProposal.from_record(
            {
                **current.to_record(),
                "status": next_status.value,
                "updated_at": utc_now(),
                "applied_at": utc_now() if next_status == SourceStrategyProposalStatus.APPLIED else None,
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update source_strategy_proposals
                set status = ?, record_json = ?, updated_at = ?
                where proposal_id = ?
                """,
                (
                    updated.status.value,
                    self._dump(updated.to_record()),
                    updated.updated_at,
                    proposal_id,
                ),
            )
        return updated

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists source_strategy_proposals (
                    proposal_id text primary key,
                    source_id text not null,
                    workflow_id text,
                    tooling_id text not null,
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

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SourceStrategyWorkshopService:
    def __init__(
        self,
        *,
        source_store: SourceStore,
        proposal_store: SourceStrategyProposalStore,
        tooling_store: Any | None = None,
    ):
        self.source_store = source_store
        self.proposal_store = proposal_store
        self.tooling_store = tooling_store

    def propose_from_tooling(self, tooling_id: str) -> SourceStrategyProposal:
        if self.tooling_store is None:
            raise ValueError("tooling_store is required to propose from tooling")
        request = self.tooling_store.get(tooling_id)
        if request.capability != "source:strategy_tuning":
            raise ValueError(f"unsupported tooling capability: {request.capability}")
        reports = list(request.payload.get("quality_reports") or [])
        if not reports:
            raise ValueError("source strategy tuning request has no quality reports")
        source_id = str(reports[0].get("source_id") or "")
        if not source_id:
            raise ValueError("quality report does not include source_id")
        source = self.source_store.get_source(source_id)
        proposal = SourceStrategyProposal(
            source_id=source.source_id,
            workflow_id=request.workflow_id,
            run_id=str(request.payload.get("run_id") or ""),
            tooling_id=request.tooling_id,
            current_metadata=dict(source.metadata),
            proposed_metadata=propose_source_metadata(source, reports, request.payload),
            rationale=_rationale(reports, request.payload),
            quality_reports=reports,
            candidate_actions=list(request.payload.get("candidate_actions") or []),
        )
        return self.proposal_store.add(proposal)

    def apply(self, proposal_id: str) -> SourceStrategyProposal:
        proposal = self.proposal_store.get(proposal_id)
        if proposal.status != SourceStrategyProposalStatus.PENDING:
            raise ValueError(f"source strategy proposal is not pending: {proposal_id}")
        source = self.source_store.get_source(proposal.source_id)
        updated = SourceDefinition.from_record(
            {
                **source.to_record(),
                "metadata": proposal.proposed_metadata,
                "updated_at": utc_now(),
            }
        )
        self.source_store.update_source(updated)
        applied = self.proposal_store.transition(proposal_id, SourceStrategyProposalStatus.APPLIED)
        if self.tooling_store is not None:
            try:
                from agentic.tooling import ToolingStatus

                self.tooling_store.transition(proposal.tooling_id, ToolingStatus.IN_PROGRESS)
            except Exception:
                pass
        return applied

    def reject(self, proposal_id: str) -> SourceStrategyProposal:
        return self.proposal_store.transition(proposal_id, SourceStrategyProposalStatus.REJECTED)


def propose_source_metadata(
    source: SourceDefinition,
    quality_reports: list[dict[str, Any]],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(source.metadata)
    if source.kind != SourceKind.WEB_PAGE:
        metadata["strategy_note"] = "quality failure requires a collector-specific strategy review"
        return metadata

    extraction = dict(metadata.get("extract") or {})
    extraction["limit"] = max(int(extraction.get("limit") or 0), 20)
    extraction["min_text_chars"] = max(int(extraction.get("min_text_chars") or 0), 4)
    extraction["href_excludes"] = _unique([*list(extraction.get("href_excludes") or []), "#"])
    extraction["text_excludes"] = _unique(
        [
            *list(extraction.get("text_excludes") or []),
            *_navigation_excludes_from_reports(quality_reports),
            *_default_navigation_excludes(),
        ]
    )
    extraction["text_exclude_regexes"] = _unique(
        [
            *list(extraction.get("text_exclude_regexes") or []),
            *_text_exclude_regexes_from_reports(quality_reports),
        ]
    )
    inferred_href = _infer_link_pattern(source.locator)
    if inferred_href:
        extraction["href_contains"] = _unique(
            [*list(extraction.get("href_contains") or []), inferred_href]
        )
    required_href_fragments = _required_href_fragments(source.locator)
    if required_href_fragments:
        extraction["href_contains_all"] = _unique(
            [*list(extraction.get("href_contains_all") or []), *required_href_fragments]
        )
    metadata["extract"] = extraction
    quality = dict(metadata.get("quality") or {})
    quality["min_score"] = int(quality.get("min_score") or 55)
    quality["min_items"] = max(int(quality.get("min_items") or 0), 3)
    metadata["quality"] = quality
    metadata["strategy"] = {
        "last_reason": "source_quality_failed",
        "updated_from_tooling": (payload or {}).get("run_id", ""),
        "candidate_actions": list((payload or {}).get("candidate_actions") or []),
    }
    return metadata


def _navigation_excludes_from_reports(reports: list[dict[str, Any]]) -> list[str]:
    examples = [str(example) for report in reports for example in report.get("examples", [])]
    excludes: list[str] = []
    for term in sorted(NAVIGATION_TERMS, key=len, reverse=True):
        if len(term) < 3:
            continue
        lowered = term.casefold()
        if any(lowered in example.casefold() for example in examples):
            excludes.append(term)
    return excludes


def _default_navigation_excludes() -> list[str]:
    return [
        "공지",
        "이용 안내",
        "갤러리 이용 안내",
        "로그인",
        "회원가입",
        "통합검색",
        "바로가기",
    ]


def _text_exclude_regexes_from_reports(reports: list[dict[str, Any]]) -> list[str]:
    examples = [str(example).strip() for report in reports for example in report.get("examples", [])]
    regexes: list[str] = []
    if any(example.startswith("[") and example.endswith("]") for example in examples):
        regexes.append(r"^\[[0-9]+\]$")
    regexes.append(r"^\[[0-9]+\]$")
    return _unique(regexes)


def _infer_link_pattern(locator: str) -> str:
    parsed = urlparse(locator)
    parts = [part for part in parsed.path.split("/") if part]
    if "lists" in parts:
        index = parts.index("lists")
        revised = parts[:]
        revised[index] = "view"
        return "/" + "/".join(revised[: index + 1])
    if len(parts) >= 2 and parts[0] == "r":
        return f"/r/{parts[1]}/comments"
    return ""


def _required_href_fragments(locator: str) -> list[str]:
    parsed = urlparse(locator)
    fragments: list[str] = []
    query = parse_qs(parsed.query)
    for key in ("id", "board", "forum", "subreddit", "community"):
        values = query.get(key)
        if values and values[0]:
            fragments.append(f"{key}={values[0]}")
    return fragments


def _rationale(reports: list[dict[str, Any]], payload: dict[str, Any]) -> str:
    reasons = sorted({reason for report in reports for reason in report.get("reasons", [])})
    actions = list(payload.get("candidate_actions") or [])
    return (
        "Proposes a source metadata strategy revision from quality-gate evidence. "
        f"Reasons: {', '.join(reasons) or 'unknown'}. "
        f"Actions: {', '.join(actions) or 'none'}."
    )


def _unique(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = str(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
