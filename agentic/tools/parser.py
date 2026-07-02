from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    tool: str
    arguments: dict[str, Any]


def parse_tool_call(raw: str) -> ToolCall:
    raw = _extract_tool_json(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid tool call JSON: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValueError("tool call must be a JSON object")
    if not isinstance(data.get("tool"), str) or not data["tool"]:
        raise ValueError("tool call requires non-empty string field 'tool'")
    if not isinstance(data.get("arguments"), dict):
        raise ValueError("tool call requires object field 'arguments'")

    return ToolCall(tool=data["tool"], arguments=data["arguments"])


def _extract_tool_json(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    if stripped.startswith("{"):
        return stripped
    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            candidate, end = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "tool" in candidate and "arguments" in candidate:
            return stripped[index : index + end]
    return stripped
