from __future__ import annotations

import json
import re


_END_MARKER_RE = re.compile(r"\s*\[end of text\]\s*$")
_CHANNEL_MARKER_RE = re.compile(r"<\|channel\>(thought|analysis|final|answer)")
_TIMING_LINE_PREFIXES = (
    "total time:",
    "throughput:",
)


def sanitize_model_output(text: str) -> str:
    """Return user-facing text from raw llama.cpp stdout."""
    cleaned = _drop_timing_lines(text.strip())
    cleaned = _extract_json_answer(cleaned) or cleaned
    if "<channel|>" in cleaned:
        cleaned = cleaned.rsplit("<channel|>", 1)[-1]
    cleaned = _strip_internal_channels(cleaned)
    cleaned = cleaned.replace("<|channel>final", "")
    cleaned = cleaned.replace("<|channel>answer", "")
    cleaned = _END_MARKER_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    if _looks_like_partial_decision(cleaned):
        return ""
    return cleaned


def sanitize_user_facing_answer(text: str) -> str:
    cleaned = sanitize_model_output(text)
    return _extract_json_answer(cleaned) or cleaned


def _drop_timing_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(_TIMING_LINE_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines)


def _extract_json_answer(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    answer = data.get("answer")
    return answer.strip() if isinstance(answer, str) else ""


def _strip_internal_channels(text: str) -> str:
    markers = list(_CHANNEL_MARKER_RE.finditer(text))
    if not markers:
        return text
    final_markers = [
        marker for marker in markers if marker.group(1) in {"final", "answer"}
    ]
    if final_markers:
        start = final_markers[-1].end()
        return text[start:]
    return _extract_explicit_answer_from_internal_text(text)


def _extract_explicit_answer_from_internal_text(text: str) -> str:
    patterns = [
        r"Direct answer:\s*\"([^\"]+)\"",
        r"Final answer:\s*\"([^\"]+)\"",
        r"Answer:\s*\"([^\"]+)\"",
        r"답변:\s*\"([^\"]+)\"",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _looks_like_partial_decision(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith('{"decision"') or stripped.startswith('{"action"'):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        if not isinstance(data, dict):
            return True
        action = data.get("action", data.get("decision"))
        if action == "answer" and isinstance(data.get("answer"), str):
            return False
        if action == "delegate" and isinstance(data.get("task"), str):
            return False
        return True
    return "<|channel>thought" in stripped or "<|channel>analysis" in stripped
