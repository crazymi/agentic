from __future__ import annotations

from agentic.tools.base import ToolSpec


def add(a: int | float, b: int | float) -> int | float:
    return a + b


ADD_TOOL = ToolSpec(
    name="add",
    description="Return the sum of two numbers.",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
    fn=add,
)
