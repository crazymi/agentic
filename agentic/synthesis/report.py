from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from agentic.models.local_gguf import LocalGGUFProvider


class ReportSynthesizer(Protocol):
    def synthesize(
        self,
        *,
        spec: Any,
        items: list[dict[str, Any]],
        analyze: dict[str, Any],
    ) -> "ReportSynthesisResult":
        ...


@dataclass(frozen=True)
class ReportInsight:
    claim: str
    evidence_ids: list[int]
    implication: str = ""
    confidence: str = "medium"

    def to_record(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "evidence_ids": list(self.evidence_ids),
            "implication": self.implication,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ReportSynthesisResult:
    ok: bool
    mode: str
    insights: list[ReportInsight] = field(default_factory=list)
    model_id: str = ""
    text: str = ""
    error: str = ""
    evidence_count: int = 0

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "model_id": self.model_id,
            "insights": [insight.to_record() for insight in self.insights],
            "text": self.text,
            "error": self.error,
            "evidence_count": self.evidence_count,
        }


class ModelReportSynthesizer:
    def __init__(
        self,
        provider: LocalGGUFProvider,
        *,
        max_evidence: int = 5,
        min_insights: int = 1,
    ):
        self.provider = provider
        self.max_evidence = max_evidence
        self.min_insights = min_insights

    def synthesize(
        self,
        *,
        spec: Any,
        items: list[dict[str, Any]],
        analyze: dict[str, Any],
    ) -> ReportSynthesisResult:
        evidence = _evidence_records(items, limit=self.max_evidence)
        if not evidence:
            return ReportSynthesisResult(
                ok=False,
                mode="model",
                model_id=self.provider.config.model_id,
                error="no_evidence",
            )
        prompt = _synthesis_prompt(spec, evidence, analyze)
        try:
            response = self.provider.generate(prompt)
        except Exception as exc:
            return ReportSynthesisResult(
                ok=False,
                mode="model",
                model_id=self.provider.config.model_id,
                error=f"{exc.__class__.__name__}: {exc}",
                evidence_count=len(evidence),
            )
        parsed = parse_synthesis_text(
            response.text or response.raw_text,
            evidence_count=len(evidence),
            min_insights=self.min_insights,
        )
        return ReportSynthesisResult(
            ok=parsed.ok,
            mode="model",
            model_id=self.provider.config.model_id,
            insights=parsed.insights,
            text=response.text[:2000],
            error=parsed.error,
            evidence_count=len(evidence),
        )


def parse_synthesis_text(
    text: str,
    *,
    evidence_count: int,
    min_insights: int = 2,
) -> ReportSynthesisResult:
    candidate_sets = [
        candidates
        for candidates in (
            _parse_json_insights(text),
            _parse_claim_blocks(text),
            _parse_line_insights(text),
        )
        if candidates
    ]
    valid_sets = [
        _valid_insights(candidates, evidence_count=evidence_count)
        for candidates in candidate_sets
    ]
    valid_sets = [items for items in valid_sets if items]
    insights = max(valid_sets, key=len) if valid_sets else []
    error = ""
    if len(insights) < min_insights:
        error = "insufficient_grounded_insights"
    return ReportSynthesisResult(
        ok=not error,
        mode="parsed",
        insights=insights,
        text=text[:2000],
        error=error,
        evidence_count=evidence_count,
    )


def _synthesis_prompt(
    spec: Any,
    evidence: list[dict[str, Any]],
    analyze: dict[str, Any],
) -> str:
    lines = [
        "아래 번호가 붙은 게시글 근거만 사용해서 반복 주제/투자심리 신호 2-3개를 뽑아라.",
        "설명 없이 JSON 하나만 출력하라.",
        '{"insights":[{"claim":"...","evidence_ids":[1,2],"implication":"...","confidence":"low|medium|high"}]}',
        "",
        f"상위 키워드: {', '.join(str(item) for item in analyze.get('top_keywords', [])[:5])}",
        "",
        "근거:",
    ]
    for item in evidence:
        lines.append(
            "[{id}] {title} | {text} | {uri}".format(
                id=item["id"],
                title=item["title"],
                text=item["text"],
                uri=item["uri"],
            )
        )
    lines.extend(
        [
            "",
            "각 insight는 evidence_ids를 1개 이상 포함해야 한다.",
            "근거가 약하면 claim에 '저신호'라고 써라.",
        ]
    )
    return "\n".join(lines)


def _evidence_records(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(items[:limit], start=1):
        title = _compact(str(item.get("title") or item.get("text") or "Untitled"), limit=100)
        text = _compact(str(item.get("text") or title), limit=180)
        uri = _compact(str(item.get("uri") or ""), limit=180)
        records.append({"id": index, "title": title, "text": text, "uri": uri})
    return records


def _parse_json_insights(text: str) -> list[ReportInsight] | None:
    raw = _extract_json_object(text)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and "insights" not in payload and isinstance(payload.get("answer"), str):
        nested = _parse_json_insights(str(payload["answer"]))
        if nested is not None:
            return nested
    raw_insights = payload.get("insights") if isinstance(payload, dict) else None
    if not isinstance(raw_insights, list):
        return None
    insights: list[ReportInsight] = []
    for item in raw_insights:
        if not isinstance(item, dict):
            continue
        insights.append(
            ReportInsight(
                claim=str(item.get("claim") or item.get("insight") or "").strip(),
                evidence_ids=_parse_evidence_ids(item.get("evidence_ids") or item.get("evidence")),
                implication=str(item.get("implication") or item.get("why_it_matters") or "").strip(),
                confidence=str(item.get("confidence") or "medium").strip() or "medium",
            )
        )
    return insights


def _parse_line_insights(text: str) -> list[ReportInsight]:
    insights: list[ReportInsight] = []
    for line in text.splitlines():
        stripped = line.strip(" -*")
        if not stripped:
            continue
        if not re.search(r"insight|인사이트|signal|시그널", stripped, flags=re.IGNORECASE):
            continue
        evidence_ids = [int(match) for match in re.findall(r"\b([1-9][0-9]?)\b", stripped)]
        claim = re.sub(r"^(insight|signal|인사이트|시그널)\s*[0-9]*\s*[:.-]?\s*", "", stripped, flags=re.IGNORECASE)
        insights.append(ReportInsight(claim=claim.strip(), evidence_ids=evidence_ids))
    return insights


def _parse_claim_blocks(text: str) -> list[ReportInsight] | None:
    lines = [line.strip(" -*") for line in text.splitlines()]
    insights: list[ReportInsight] = []
    current: dict[str, Any] = {}
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("claim:"):
            if current:
                insight = _insight_from_claim_block(current)
                if insight is not None:
                    insights.append(insight)
            current = {"claim": line.split(":", 1)[1].strip()}
            continue
        if (
            lowered.startswith("evidence:")
            or lowered.startswith("evidence_ids:")
            or lowered.startswith("evidence id:")
        ) and current:
            current["evidence_ids"] = _parse_evidence_ids(line.split(":", 1)[1])
            continue
        if lowered.startswith("implication:") and current:
            current["implication"] = line.split(":", 1)[1].strip()
            continue
        if lowered.startswith("confidence:") and current:
            current["confidence"] = line.split(":", 1)[1].strip().lower().rstrip(".")
            continue
    if current:
        insight = _insight_from_claim_block(current)
        if insight is not None:
            insights.append(insight)
    return insights or None


def _insight_from_claim_block(record: dict[str, Any]) -> ReportInsight | None:
    claim = str(record.get("claim") or "").strip()
    evidence_ids = _parse_evidence_ids(record.get("evidence_ids") or "")
    if not claim or not evidence_ids:
        return None
    return ReportInsight(
        claim=claim,
        evidence_ids=evidence_ids,
        implication=str(record.get("implication") or "").strip(),
        confidence=str(record.get("confidence") or "medium").strip() or "medium",
    )


def _valid_insights(
    insights: list[ReportInsight],
    *,
    evidence_count: int,
) -> list[ReportInsight]:
    valid: list[ReportInsight] = []
    seen: set[str] = set()
    for insight in insights:
        claim = _clean_claim(insight.claim)
        evidence_ids = sorted({item for item in insight.evidence_ids if 1 <= item <= evidence_count})
        if len(claim) < 10 or not evidence_ids or _is_meta_claim(claim):
            continue
        key = claim.casefold()
        if key in seen:
            continue
        seen.add(key)
        valid.append(
            ReportInsight(
                claim=claim,
                evidence_ids=evidence_ids,
                implication=" ".join(insight.implication.split()),
                confidence=insight.confidence if insight.confidence in {"low", "medium", "high"} else "medium",
            )
        )
    return valid[:4]


def _clean_claim(claim: str) -> str:
    cleaned = " ".join(str(claim or "").split())
    if re.search(r"\bclaim\s*:", cleaned, flags=re.IGNORECASE):
        cleaned = re.split(r"\bclaim\s*:", cleaned, flags=re.IGNORECASE)[-1].strip()
    cleaned = re.sub(r"\(?(?:evidence|근거)\s*\[[^\]]+\]\)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -.;")
    return cleaned


def _is_meta_claim(claim: str) -> bool:
    normalized = claim.casefold()
    meta_terms = (
        "output format",
        "constraint",
        "goal:",
        "task:",
        "json only",
        "specific shape",
        "provided evidence",
        "numbered evidence",
        "extract 2-3",
        "2-3 repetitive",
        "wait,",
        "i need",
        "need 2-3",
        "write 2-4",
        "evidence_id",
        "return json",
    )
    return any(term in normalized for term in meta_terms)


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return ""
    return text[start : end + 1]


def _parse_evidence_ids(value: Any) -> list[int]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.findall(r"\d+", str(value or ""))
    ids: list[int] = []
    for item in raw:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _compact(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
