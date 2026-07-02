from __future__ import annotations

from dataclasses import dataclass, field
import re
from urllib.parse import parse_qs, urlparse

from agentic.sources.models import SourceItem


NAVIGATION_TERMS = {
    "jump to content",
    "get new reddit",
    "log in",
    "login",
    "sign up",
    "popular",
    "all",
    "random",
    "users",
    "apps",
    "advertise",
    "terms",
    "privacy",
    "help",
    "바로가기",
    "로그인",
    "회원가입",
    "통합검색",
    "페이지",
    "상단",
    "하단",
    "공지",
    "개념글",
    "야간모드",
    "이용 안내",
    "갤러리 이용 안내",
}


@dataclass(frozen=True)
class SourceQualityReport:
    item_count: int
    score: int
    ok: bool
    min_score: int
    min_items: int
    nav_like_count: int = 0
    short_text_count: int = 0
    duplicate_text_count: int = 0
    off_path_count: int = 0
    reasons: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def to_record(self) -> dict:
        return {
            "item_count": self.item_count,
            "score": self.score,
            "ok": self.ok,
            "min_score": self.min_score,
            "min_items": self.min_items,
            "nav_like_count": self.nav_like_count,
            "short_text_count": self.short_text_count,
            "duplicate_text_count": self.duplicate_text_count,
            "off_path_count": self.off_path_count,
            "reasons": list(self.reasons),
            "examples": list(self.examples),
        }


def evaluate_source_quality(
    items: list[SourceItem],
    *,
    source_url: str = "",
    min_score: int = 55,
    min_items: int = 3,
) -> SourceQualityReport:
    item_count = len(items)
    if item_count == 0:
        return SourceQualityReport(
            item_count=0,
            score=0,
            ok=False,
            min_score=min_score,
            min_items=min_items,
            reasons=["no_items_collected"],
        )

    source_identity = _source_identity(source_url)
    nav_like_count = 0
    short_text_count = 0
    off_path_count = 0
    seen_texts: set[str] = set()
    duplicate_text_count = 0
    examples: list[str] = []

    for item in items:
        text = _item_text(item)
        normalized = _normalize_text(text)
        if normalized in seen_texts:
            duplicate_text_count += 1
        seen_texts.add(normalized)
        if _is_short_text(text):
            short_text_count += 1
        if _is_navigation_like(item, normalized):
            nav_like_count += 1
        if source_identity and _is_off_source_identity(item.uri, source_identity):
            off_path_count += 1
        if len(examples) < 5:
            examples.append(text[:120])

    nav_ratio = nav_like_count / item_count
    short_ratio = short_text_count / item_count
    duplicate_ratio = duplicate_text_count / item_count
    off_path_ratio = off_path_count / item_count
    score = 100
    score -= round(nav_ratio * 55)
    score -= round(short_ratio * 25)
    score -= round(duplicate_ratio * 20)
    score -= round(off_path_ratio * 35)
    if item_count < min_items:
        score = min(score, 40)
    score = max(0, min(100, score))

    reasons: list[str] = []
    if item_count < min_items:
        reasons.append("too_few_items")
    if nav_ratio >= 0.35:
        reasons.append("navigation_like_items")
    if short_ratio >= 0.45:
        reasons.append("short_text_items")
    if duplicate_ratio >= 0.35:
        reasons.append("duplicate_text_items")
    if off_path_ratio >= 0.50:
        reasons.append("off_source_path_items")
    if score < min_score:
        reasons.append("score_below_threshold")

    return SourceQualityReport(
        item_count=item_count,
        score=score,
        ok=item_count >= min_items and score >= min_score and not reasons,
        min_score=min_score,
        min_items=min_items,
        nav_like_count=nav_like_count,
        short_text_count=short_text_count,
        duplicate_text_count=duplicate_text_count,
        off_path_count=off_path_count,
        reasons=reasons,
        examples=examples,
    )


def quality_thresholds(metadata: dict) -> tuple[int, int]:
    raw = metadata.get("quality") if isinstance(metadata, dict) else None
    config = raw if isinstance(raw, dict) else {}
    return int(config.get("min_score") or 55), int(config.get("min_items") or 1)


def _item_text(item: SourceItem) -> str:
    return " ".join(part.strip() for part in [item.title, item.content_text] if part and part.strip())


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _is_short_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    return len(stripped) < 8


def _is_navigation_like(item: SourceItem, normalized: str) -> bool:
    if _contains_navigation_term(normalized):
        return True
    if re.fullmatch(r"(\[[0-9]+\]\s*)+", normalized):
        return True
    parsed = urlparse(item.uri)
    if parsed.scheme in {"javascript", "mailto", "tel"}:
        return True
    if parsed.fragment and not parsed.path.strip("/"):
        return True
    if normalized.isdigit():
        return True
    return False


def _contains_navigation_term(normalized: str) -> bool:
    tokens = set(normalized.split())
    for term in NAVIGATION_TERMS:
        normalized_term = term.casefold()
        if " " not in normalized_term and normalized_term.isascii():
            if len(normalized) > max(32, len(normalized_term) + 12):
                continue
            if normalized_term in tokens:
                return True
            continue
        if normalized_term in normalized:
            return True
    return False


@dataclass(frozen=True)
class SourceIdentity:
    netloc: str
    path_prefix: str
    query_keys: dict[str, str] = field(default_factory=dict)


def _source_identity(source_url: str) -> SourceIdentity | None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        path_prefix = ""
    else:
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "r":
            path_prefix = "/" + "/".join(parts[:2])
        elif len(parts) >= 2 and parts[0] == "board":
            path_prefix = "/" + parts[0]
        else:
            path_prefix = "/" + parts[0]
    return SourceIdentity(
        netloc=parsed.netloc,
        path_prefix=path_prefix,
        query_keys=_identity_query_keys(parsed.query),
    )


def _identity_query_keys(query: str) -> dict[str, str]:
    values = parse_qs(query)
    identity: dict[str, str] = {}
    for key in ("id", "board", "forum", "subreddit", "community"):
        raw_values = values.get(key)
        if raw_values and raw_values[0]:
            identity[key] = raw_values[0]
    return identity


def _is_off_source_identity(item_url: str, source_identity: SourceIdentity) -> bool:
    item = urlparse(item_url)
    if source_identity.netloc and item.netloc and source_identity.netloc != item.netloc:
        return True
    if source_identity.path_prefix and item.path:
        if not item.path.startswith(source_identity.path_prefix):
            return True
    if source_identity.query_keys:
        values = parse_qs(item.query)
        for key, expected in source_identity.query_keys.items():
            actual_values = values.get(key)
            if not actual_values:
                return True
            if actual_values[0] != expected:
                return True
    if not item.path:
        return False
    return False
