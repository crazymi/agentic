from __future__ import annotations

from dataclasses import dataclass, field


REQUIRED_REPORT_SECTIONS = (
    "## Executive Summary",
    "## Evidence",
    "## Signals",
    "## Source Quality",
    "## Next Watch Points",
)


@dataclass(frozen=True)
class ReportQualityReport:
    ok: bool
    score: int
    reasons: list[str] = field(default_factory=list)
    section_count: int = 0
    evidence_count: int = 0
    signal_count: int = 0
    char_count: int = 0
    min_score: int = 70

    def to_record(self) -> dict:
        return {
            "ok": self.ok,
            "score": self.score,
            "reasons": list(self.reasons),
            "section_count": self.section_count,
            "evidence_count": self.evidence_count,
            "signal_count": self.signal_count,
            "char_count": self.char_count,
            "min_score": self.min_score,
        }


def evaluate_report_quality(
    content: str,
    *,
    min_score: int = 70,
    min_chars: int = 280,
    min_evidence: int = 3,
    min_signals: int = 3,
) -> ReportQualityReport:
    text = content or ""
    lines = [line.rstrip() for line in text.splitlines()]
    section_count = sum(1 for section in REQUIRED_REPORT_SECTIONS if section in text)
    evidence_count = _count_prefixed_items(lines, prefix="- ")
    signal_count = _count_section_items(lines, "## Signals")
    char_count = len(text.strip())
    score = 100
    reasons: list[str] = []

    missing_sections = [section for section in REQUIRED_REPORT_SECTIONS if section not in text]
    if missing_sections:
        score -= min(35, 7 * len(missing_sections))
        reasons.append("missing_required_sections")
    if char_count < min_chars:
        score -= 20
        reasons.append("report_too_short")
    if evidence_count < min_evidence:
        score -= 20
        reasons.append("insufficient_evidence")
    if signal_count < min_signals:
        score -= 20
        reasons.append("insufficient_signals")
    if "No analysis summary" in text or "untitled" in text:
        score -= 10
        reasons.append("placeholder_content")

    score = max(0, min(100, score))
    return ReportQualityReport(
        ok=score >= min_score and not reasons,
        score=score,
        reasons=reasons,
        section_count=section_count,
        evidence_count=evidence_count,
        signal_count=signal_count,
        char_count=char_count,
        min_score=min_score,
    )


def _count_prefixed_items(lines: list[str], *, prefix: str) -> int:
    return sum(1 for line in lines if line.strip().startswith(prefix))


def _count_section_items(lines: list[str], section: str) -> int:
    in_section = False
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped == section:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            count += 1
    return count
