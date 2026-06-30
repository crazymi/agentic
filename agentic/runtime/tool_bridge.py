from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.tools.parser import ToolCall, parse_tool_call
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class ToolExecutionResult:
    tool: str | None
    ok: bool
    result: Any = None
    error_type: str | None = None
    error_message: str | None = None


class ToolBridge:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        trace: TraceLogger | None = None,
    ):
        self.registry = registry or ToolRegistry.with_defaults()
        self.trace = trace

    def execute_tool_call_text(self, text: str) -> ToolExecutionResult:
        try:
            call = parse_tool_call(text)
        except ValueError as exc:
            return ToolExecutionResult(
                tool=None,
                ok=False,
                error_type="malformed_tool_call",
                error_message=str(exc),
            )

        self._record_tool_called(call)

        try:
            result = self.registry.execute(call)
        except KeyError as exc:
            return self._record_failure(
                call,
                error_type="unknown_tool",
                error_message=str(exc),
            )
        except TypeError as exc:
            return self._record_failure(
                call,
                error_type="invalid_tool_arguments",
                error_message=str(exc),
            )

        execution_result = ToolExecutionResult(
            tool=call.tool,
            ok=True,
            result=result,
        )
        if self.trace is not None:
            self.trace.record(
                f"tool_result:{call.tool}",
                {"tool": call.tool, "ok": True, "result": result},
            )
        return execution_result

    def _record_tool_called(self, call: ToolCall) -> None:
        if self.trace is None:
            return
        self.trace.record(
            f"tool_called:{call.tool}",
            {"tool": call.tool, "arguments": call.arguments},
        )

    def _record_failure(
        self,
        call: ToolCall,
        *,
        error_type: str,
        error_message: str,
    ) -> ToolExecutionResult:
        result = ToolExecutionResult(
            tool=call.tool,
            ok=False,
            error_type=error_type,
            error_message=error_message,
        )
        if self.trace is not None:
            self.trace.record(
                f"tool_result:{call.tool}",
                {
                    "tool": call.tool,
                    "ok": False,
                    "error_type": error_type,
                    "error_message": error_message,
                },
            )
        return result
