from __future__ import annotations

from typing import Any

from agentic.tools.add import ADD_TOOL
from agentic.tools.base import ToolSpec
from agentic.tools.parser import ToolCall


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec] | None = None):
        self._tools = {tool.name: tool for tool in (tools or [])}

    @classmethod
    def with_defaults(cls) -> "ToolRegistry":
        return cls([ADD_TOOL])

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, call: ToolCall) -> Any:
        if call.tool not in self._tools:
            raise KeyError(f"unknown tool: {call.tool}")
        return self._tools[call.tool].fn(**call.arguments)
