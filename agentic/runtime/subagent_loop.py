from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Protocol

from agentic.agents.subagent import SubAgent
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.runtime.tool_bridge import ToolBridge, ToolExecutionResult
from agentic.skills.registry import SkillRegistry
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
        skills: SkillRegistry | None = None,
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
                skills=skills,
            )

        self.agent = agent
        self.tool_bridge = tool_bridge or ToolBridge(registry=tools, trace=trace)
        self.trace = trace
        self.max_tool_call_retries = 1

    def run_once(self, task: SubAgentTask) -> SubagentLoopResult:
        try:
            task.transition(TaskState.RUNNING)
            tool_result: ToolExecutionResult | None = None
            active_task = task
            for attempt in range(self.max_tool_call_retries + 1):
                self._record(
                    "subagent_model_called",
                    {
                        "task_id": task.task_id,
                        "instruction": active_task.instruction,
                        "attempt": attempt + 1,
                        "skills": _selected_skill_names(self.agent, active_task),
                    },
                )

                model_response = self._generate_for_task(active_task)
                tool_call_text = self._response_text(model_response).strip()
                tool_result = self.tool_bridge.execute_tool_call_text(tool_call_text)
                if tool_result.ok:
                    break
                recovered_tool_call = _recover_skill_workshop_tool_call(
                    instruction=task.instruction,
                    output=tool_call_text,
                ) or _recover_workflow_spec_tool_call(
                    instruction=task.instruction,
                    output=tool_call_text,
                )
                if recovered_tool_call is not None:
                    recovered_tool = _tool_name_from_tool_call(recovered_tool_call)
                    self._record(
                        "subagent_tool_call_recovered",
                        {
                            "task_id": task.task_id,
                            "attempt": attempt + 1,
                            "tool": recovered_tool,
                            "text_chars": len(tool_call_text),
                        },
                    )
                    tool_result = self.tool_bridge.execute_tool_call_text(recovered_tool_call)
                    if tool_result.ok:
                        break
                if tool_result.error_type != "malformed_tool_call" or attempt >= self.max_tool_call_retries:
                    task.transition(TaskState.TOOL_REQUESTED)
                    return self._fail(
                        task,
                        tool_result.error_type or "tool_execution_failed",
                        tool_result.error_message or "tool execution failed",
                    )
                self._record(
                    "subagent_tool_call_retry",
                    {
                        "task_id": task.task_id,
                        "attempt": attempt + 1,
                        "error_type": tool_result.error_type,
                        "error_message": tool_result.error_message,
                        "text_chars": len(tool_call_text),
                        "text_preview": _preview(tool_call_text),
                    },
                )
                active_task = SubAgentTask(
                    instruction=_retry_instruction(
                        original_instruction=task.instruction,
                        previous_output=tool_call_text,
                        error_message=tool_result.error_message or "malformed tool call",
                    ),
                    task_id=task.task_id,
                )

            if tool_result is None:
                return self._fail(task, "tool_execution_failed", "tool execution failed")

            task.transition(TaskState.TOOL_REQUESTED)
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
        if isinstance(text, str) and text.strip():
            return text
        raw_text = getattr(model_response, "raw_text", None)
        if isinstance(raw_text, str):
            return raw_text
        if isinstance(text, str):
            return text
        raise TypeError("subagent response must be text or expose a text attribute")

    def _generate_for_task(self, task: SubAgentTask) -> Any:
        try:
            return self.agent.generate_for_task(task, trace=self.trace)
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            return self.agent.generate_for_task(task)

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


def _retry_instruction(
    *,
    original_instruction: str,
    previous_output: str,
    error_message: str,
) -> str:
    if _looks_like_workflow_spec_retry(original_instruction, previous_output):
        return (
            "Your previous output was not a valid workflow_spec tool call. "
            f"Parser error: {error_message}. "
            "Retry the same task, but output exactly one compact JSON object and no commentary. "
            "Use this exact shape: "
            '{"tool":"workflow_spec","arguments":{"action":"create","name":"Recurring Trend Workflow",'
            '"goal":"Create a recurring trend report from selected sources.",'
            '"description":"Generic recurring source monitoring workflow.",'
            '"trigger":"interval:60s","source":"selected_source",'
            '"step_types":["collect","analyze","report","notify"],'
            '"output":"report",'
            '"success_criteria":["A reviewable report is produced."],'
            '"assumptions":["Credentials and connector details are reviewed later."],'
            '"capabilities":[{"capability":"source_collect"},{"capability":"resource_store"}],'
            '"policy":{"approval":"required for external submit or writes"}}}. '
            "Keep every string short. "
            f"Original task: {original_instruction}. "
            f"Previous output length: {len(previous_output)} characters."
        )
    if "source_candidate" in original_instruction:
        return (
            "Your previous output was not a valid source_candidate tool call. "
            f"Parser error: {error_message}. "
            "Retry the same task, but output exactly one compact JSON object and no commentary. "
            "If the provided search results are empty, do not invent a URL. "
            "Use only short required fields. Do not include aliases, rationale, or evidence. "
            "Use this exact compact shape when a candidate exists: "
            '{"tool":"source_candidate","arguments":{"action":"create","workflow_id":"wf_id",'
            '"requested_source":"source label","kind":"web_page","name":"candidate name",'
            '"locator":"https://example.com","confidence":0.8,"auto_register":true}}. '
            f"Original task: {original_instruction}. "
            f"Previous output length: {len(previous_output)} characters."
        )
    if "web_search" in original_instruction:
        return (
            "Your previous output was not a valid web_search tool call. "
            f"Parser error: {error_message}. "
            "Retry the same task, but output exactly one compact JSON object and no commentary. "
            'Use this exact shape: {"tool":"web_search","arguments":{"query":"source name or official site","count":5,"language":"ko"}}. '
            f"Original task: {original_instruction}. "
            f"Previous output length: {len(previous_output)} characters."
        )
    return (
        "Your previous output was not a valid tool call. "
        f"Parser error: {error_message}. "
        "Retry the same task, but output exactly one JSON object and no commentary. "
        "The JSON must have this shape: "
        '{"tool":"skill_workshop","arguments":{"action":"create","name":"workflow-building",'
        '"description":"Guide vague workflow requests","proposal_body":"..."}}. '
        f"Original task: {original_instruction}. "
        f"Previous output length: {len(previous_output)} characters."
    )


def _looks_like_workflow_spec_retry(original_instruction: str, previous_output: str) -> bool:
    combined = f"{original_instruction}\n{previous_output}".lower()
    return "workflow_spec" in combined or "workflow spec" in combined or "workflowspec" in combined


def _preview(text: str, limit: int = 500) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "..."


def _selected_skill_names(agent: SubagentLike, task: SubAgentTask) -> list[str]:
    selector = getattr(agent, "selected_skill_names", None)
    if not callable(selector):
        return []
    try:
        return list(selector(task))
    except Exception:
        return []


def _recover_skill_workshop_tool_call(*, instruction: str, output: str) -> str | None:
    combined = f"{instruction}\n{output}".lower()
    if "skill_workshop" not in combined:
        return None
    if not output.strip():
        return None
    name = _extract_quoted_field(output, "name") or "workflow-building"
    description = (
        _extract_quoted_field(output, "description")
        or "Guide vague workflow requests"
    )
    body = _extract_proposal_body(output) or _strip_channel_prefixes(output)
    return json.dumps(
        {
            "tool": "skill_workshop",
            "arguments": {
                "action": "create",
                "name": name,
                "description": description[:120],
                "proposal_body": body,
                "metadata": {"recovered_from": "natural_language_tool_intent"},
            },
        },
        ensure_ascii=False,
    )


def _recover_workflow_spec_tool_call(*, instruction: str, output: str) -> str | None:
    combined = f"{instruction}\n{output}".lower()
    if "workflow_spec" not in combined and "workflow spec" not in combined and "workflowspec" not in combined:
        return None
    candidate = _extract_workflow_spec_arguments(output)
    if candidate is None:
        return None
    return json.dumps(
        {
            "tool": "workflow_spec",
            "arguments": {
                "action": "create",
                **candidate,
            },
        },
        ensure_ascii=False,
    )


def _extract_workflow_spec_arguments(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    stripped = _strip_channel_prefixes(text)
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            candidate, _end = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(candidate, dict):
            continue
        args = candidate.get("arguments") if isinstance(candidate.get("arguments"), dict) else candidate
        if _looks_like_workflow_spec_arguments(args):
            return _normalize_workflow_spec_arguments(args)
    repaired = _extract_compact_workflow_spec_fields(stripped)
    if repaired and _looks_like_workflow_spec_arguments(repaired):
        return _normalize_workflow_spec_arguments(repaired)
    return None


def _looks_like_workflow_spec_arguments(args: dict[str, Any]) -> bool:
    return (
        isinstance(args.get("name"), str)
        and isinstance(args.get("goal"), str)
        and (
            (isinstance(args.get("steps"), list) and len(args.get("steps") or []) >= 2)
            or (isinstance(args.get("step_types"), list) and len(args.get("step_types") or []) >= 2)
        )
    )


def _normalize_workflow_spec_arguments(args: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name",
        "goal",
        "description",
        "steps",
        "step_types",
        "triggers",
        "trigger",
        "sources",
        "source",
        "outputs",
        "output",
        "success_criteria",
        "assumptions",
        "capabilities",
        "policy",
        "inputs",
        "evals",
        "owner_channel",
        "intent_type",
    }
    return {key: value for key, value in args.items() if key in allowed}


def _extract_compact_workflow_spec_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {"action": "create"}
    for key in ("name", "goal", "description", "trigger", "output"):
        value = _extract_json_string_field(text, key)
        if value:
            fields[key] = value
    source = _extract_json_string_field(text, "source")
    if source:
        fields["source"] = source
    else:
        sources = _extract_json_string_array_field(text, "source")
        if sources:
            fields["source"] = "+".join(sources)
    step_types = _extract_json_string_array_field(text, "step_types")
    if step_types:
        fields["step_types"] = step_types
    criteria = _extract_json_string_array_field(text, "success_criteria")
    if criteria:
        fields["success_criteria"] = criteria
    assumptions = _extract_json_string_array_field(text, "assumptions")
    if assumptions:
        fields["assumptions"] = assumptions
    return fields


def _extract_json_string_field(text: str, field: str) -> str:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"([^"]+)"', text)
    return match.group(1).strip() if match else ""


def _extract_json_string_array_field(text: str, field: str) -> list[str]:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*\[([^\]]+)', text, flags=re.DOTALL)
    if not match:
        return []
    return [item.strip() for item in re.findall(r'"([^"]+)"', match.group(1))]


def _tool_name_from_tool_call(tool_call_text: str) -> str:
    try:
        data = json.loads(tool_call_text)
    except json.JSONDecodeError:
        return "unknown"
    tool = data.get("tool") if isinstance(data, dict) else None
    return str(tool or "unknown")


def _extract_quoted_field(text: str, field: str) -> str:
    patterns = [
        rf"{field}`?\s*:\s*`?\"([^\"]+)\"",
        rf"{field}`?\s*:\s*`?'([^']+)'",
        rf"{field}`?\s*:\s*`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_proposal_body(text: str) -> str:
    proposal_marker = re.search(
        r"proposal_body`?\s*:?.*?```(?:markdown)?\s*(.+?)(?:```|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if proposal_marker:
        return _strip_channel_prefixes(proposal_marker.group(1)).strip()

    first_markdown_block = re.search(
        r"```(?:markdown)?\s*(.+?)(?:```|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if first_markdown_block:
        return _strip_channel_prefixes(first_markdown_block.group(1)).strip()

    bullet_block = _extract_labeled_bullet_block(text)
    if bullet_block:
        return bullet_block

    return ""


def _extract_labeled_bullet_block(text: str) -> str:
    labels = ("trigger", "interview", "discovery", "proposal", "approval", "recording", "evolution")
    lines = _strip_channel_prefixes(text).splitlines()
    collected: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        is_labeled_bullet = _labeled_bullet_label(stripped) in labels
        if is_labeled_bullet:
            collected.append(stripped)
            collecting = True
            continue
        if collecting:
            if stripped.startswith(("-", "*")):
                collected.append(stripped)
                continue
            break
    return "\n".join(collected).strip()


def _labeled_bullet_label(stripped_line: str) -> str:
    if not stripped_line.startswith(("-", "*")):
        return ""
    label_text = stripped_line[1:].strip().lower()
    label_text = label_text.lstrip("*`_ ").split(":", 1)[0]
    return label_text.strip("*`_ ")


def _strip_channel_prefixes(text: str) -> str:
    cleaned = text.replace("<|channel>thought", "").replace("<|channel>analysis", "")
    cleaned = cleaned.replace("<|channel>final", "").replace("<|channel>answer", "")
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if stripped.startswith(("total time:", "throughput:")):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
