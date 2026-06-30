from __future__ import annotations

import re


_END_MARKER_RE = re.compile(r"\s*\[end of text\]\s*$")
_TIMING_LINE_PREFIXES = (
    "total time:",
    "throughput:",
)


def sanitize_model_output(text: str) -> str:
    """Return user-facing text from raw llama.cpp stdout."""
    cleaned = _drop_timing_lines(text.strip())
    if "<channel|>" in cleaned:
        cleaned = cleaned.rsplit("<channel|>", 1)[-1]
    cleaned = cleaned.replace("<|channel>final", "")
    cleaned = cleaned.replace("<|channel>answer", "")
    cleaned = _END_MARKER_RE.sub("", cleaned)
    return cleaned.strip()


def _drop_timing_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(_TIMING_LINE_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines)
