from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agentic.agents.subagent import SubAgent
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.runtime.tool_bridge import ToolBridge, ToolExecutionResult
from agentic.tasks.subagent_task import SubAgentTask, TaskState
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


class SubagentLike(Protocol):
    def generate_for_task(self, task: SubAgentTask) -> Any:
        ...


class ToolBridgeLike(Protocol):
    def execute_tool_call_text(self, text: str) -> ToolExecutionResult:
        ...


@dataclass(frozen=True)
class SubagentLoopResult:
    task: SubAgentTask
    ok: bool
    report: str | None = None
    error_type: str | None = None
    error_message: str | None = None


class SubagentLoop:
    def __init__(
        self,
        *,
        agent: SubagentLike | None = None,
        provider: LocalGGUFProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
        tools: ToolRegistry | None = None,
        tool_bridge: ToolBridgeLike | None = None,
        trace: TraceLogger | None = None,
    ):
        tools = tools or ToolRegistry.with_defaults()
        if agent is None:
            if provider is None:
                raise ValueError("SubagentLoop requires either agent or provider")
            agent = SubAgent(
                provider=provider,
                prompt_builder=prompt_builder or PromptBuilder(),
                tools=tools,
            )

        self.agent = agent
        self.tool_bridge = tool_bridge or ToolBridge(registry=tools, trace=trace)
        self.trace = trace

    def run_once(self, task: SubAgentTask) -> SubagentLoopResult:
        try:
            task.transition(TaskState.RUNNING)
            self._record(
                "subagent_model_called",
                {"task_id": task.task_id, "instruction": task.instruction},
            )

            model_response = self.agent.generate_for_task(task)
            tool_call_text = self._response_text(model_response).strip()

            task.transition(TaskState.TOOL_REQUESTED)
            tool_result = self.tool_bridge.execute_tool_call_text(tool_call_text)
            if not tool_result.ok:
                return self._fail(
                    task,
                    tool_result.error_type or "tool_execution_failed",
                    tool_result.error_message or "tool execution failed",
                )

            task.transition(TaskState.TOOL_COMPLETED)
            report = str(tool_result.result)
            task.mark_result(report)
            self._record(
                "subagent_reported",
                {
                    "task_id": task.task_id,
                    "tool": tool_result.tool,
                    "result": tool_result.result,
                    "report": report,
                },
            )
            task.transition(TaskState.COMPLETED)
            return SubagentLoopResult(task=task, ok=True, report=report)
        except Exception as exc:
            return self._fail(task, exc.__class__.__name__, str(exc))

    def _response_text(self, model_response: Any) -> str:
        if isinstance(model_response, str):
            return model_response
        text = getattr(model_response, "text", None)
        if isinstance(text, str):
            return text
        raise TypeError("subagent response must be text or expose a text attribute")

    def _fail(
        self,
        task: SubAgentTask,
        error_type: str,
        error_message: str,
    ) -> SubagentLoopResult:
        if task.state not in {TaskState.COMPLETED, TaskState.FAILED}:
            try:
                task.transition(TaskState.FAILED)
            except ValueError:
                pass
        self._record(
            "subagent_failed",
            {
                "task_id": task.task_id,
                "state": task.state.value,
                "error_type": error_type,
                "error_message": error_message,
            },
        )
        return SubagentLoopResult(
            task=task,
            ok=False,
            error_type=error_type,
            error_message=error_message,
        )

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.trace is not None:
            self.trace.record(event_type, payload)
