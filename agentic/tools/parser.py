from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    tool: str
    arguments: dict[str, Any]


def parse_tool_call(raw: str) -> ToolCall:
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
