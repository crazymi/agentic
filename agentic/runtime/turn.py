from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from agentic.agents.master import MasterAgent
from agentic.models.local_gguf import ModelResponse
from agentic.models.response_sanitizer import sanitize_user_facing_answer
from agentic.traces.logger import TraceLogger


MasterAction = Literal["answer", "delegate"]


@dataclass(frozen=True)
class MasterDecision:
    action: MasterAction
    answer: str | None = None
    task: str | None = None

    @classmethod
    def answer_directly(cls, answer: str) -> "MasterDecision":
        cleaned = sanitize_user_facing_answer(answer) or answer.strip()
        return cls(action="answer", answer=cleaned)

    @classmethod
    def delegate(cls, task: str) -> "MasterDecision":
        return cls(action="delegate", task=task)

    @classmethod
    def parse(cls, text: str) -> "MasterDecision":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid master decision JSON") from exc

        if not isinstance(data, dict):
            raise ValueError("master decision must be a JSON object")

        action = data.get("action", data.get("decision"))
        if action == "answer":
            answer = data.get("answer")
            if not isinstance(answer, str) or not answer:
                raise ValueError("answer decision requires non-empty answer")
            return cls.answer_directly(answer)

        if action == "delegate":
            task = data.get("task")
            if not isinstance(task, str) or not task:
                raise ValueError("delegate decision requires non-empty task")
            return cls.delegate(task)

        raise ValueError("master decision action must be answer or delegate")


class MasterTurn:
    def __init__(
        self,
        agent: MasterAgent,
        trace: TraceLogger | None = None,
    ):
        self.agent = agent
        self.trace = trace

    def decide(self, user_message: str) -> MasterDecision:
        self._record(
            "master_model_called",
            {
                "message": user_message,
                "skills": _selected_skill_names(self.agent, user_message),
            },
        )
        response = self._generate(user_message)

        try:
            decision = MasterDecision.parse(response.text)
        except ValueError:
            decision = self._fallback_decision(user_message, response)

        self._record_decision(decision)
        return decision

    def _fallback_decision(
        self,
        user_message: str,
        response: ModelResponse,
    ) -> MasterDecision:
        addition = _find_simple_addition(user_message)
        if addition is not None:
            a, b = addition
            return MasterDecision.delegate(f"Use add tool to compute {a}+{b}.")
        if _looks_like_workflow_spec_request(user_message):
            return MasterDecision.delegate(_workflow_spec_task(user_message))
        if _looks_like_skill_workshop_request(user_message):
            return MasterDecision.delegate(_skill_workshop_task(user_message))
        if _looks_like_workflow_request(user_message):
            return MasterDecision.delegate(_workflow_design_task(user_message))
        answer = sanitize_user_facing_answer(response.text)
        if not answer:
            answer = "답변을 정리하지 못했습니다."
        return MasterDecision.answer_directly(answer)

    def _generate(self, user_message: str) -> ModelResponse:
        try:
            return self.agent.generate(user_message, trace=self.trace)
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            return self.agent.generate(user_message)

    def _record_decision(self, decision: MasterDecision) -> None:
        payload = {"action": decision.action}
        if decision.answer is not None:
            payload["answer"] = decision.answer
        if decision.task is not None:
            payload["task"] = decision.task
        self._record("master_delegation_decision", payload)

    def _record(self, event_type: str, payload: dict) -> None:
        if self.trace is not None:
            self.trace.record(event_type, payload)


def _find_simple_addition(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?<!\d)(\d+)\s*\+\s*(\d+)(?!\d)", text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _selected_skill_names(agent: MasterAgent, user_message: str) -> list[str]:
    selector = getattr(agent, "selected_skill_names", None)
    if not callable(selector):
        return []
    try:
        return list(selector(user_message))
    except Exception:
        return []


def _looks_like_skill_workshop_request(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("skill", "스킬", "skill.md", "proposal", "제안"))


def _looks_like_workflow_request(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "workflow",
            "워크플로우",
            "자동화",
            "주기",
            "마다",
            "크롤",
            "보고서",
            "알림",
            "watch",
            "monitor",
        )
    )


def _looks_like_workflow_spec_request(text: str) -> bool:
    lowered = text.lower()
    return "workflow_spec" in lowered or "workflow spec" in lowered or "workflowspec" in lowered


def _workflow_spec_task(user_message: str) -> str:
    compact = _compact_skill_workshop_request(user_message)
    return (
        "Create a pending WorkflowSpec using the workflow_spec tool. "
        "Do not execute, approve, activate, crawl, write scripts, or write user workflow files. "
        f"Original request and slots: {compact}. "
        "Use the compact arguments: action=create, name, goal, description, trigger, source, "
        "step_types, output, success_criteria, assumptions, capabilities, and policy. "
        "Use short strings. Prefer step_types collect, analyze, aggregate, report, notify. "
        "Output one JSON tool call only."
    )


def _skill_workshop_task(user_message: str) -> str:
    compact = _compact_skill_workshop_request(user_message)
    return (
        "Create a pending skill proposal using the skill_workshop tool. "
        "Do not write active skill files. "
        "Use name vague-workflow-builder when the request is about vague workflow building. "
        f"Original request and slots: {compact}. "
        "The proposal_body must be exactly seven short markdown bullets covering: "
        "Trigger, Interview, Discovery, Proposal, Approval, Recording, Evolution. "
        "Output one JSON tool call only."
    )


def _workflow_design_task(user_message: str) -> str:
    return (
        "Create a pending skill proposal using the skill_workshop tool for a reusable workflow-building procedure. "
        "Do not implement the user's concrete workflow and do not write active skill files. "
        "The proposal should help future agents handle vague workflow requests like: "
        f"{user_message!r}. "
        "Include how to interview the user, discover required tools/connectors/storage, propose runnable workflow specs, "
        "gate risky actions through approval, and record experience after execution."
    )


def _compact_skill_workshop_request(user_message: str, *, limit: int = 900) -> str:
    original = _extract_line_after(user_message, "Original request:")
    slots = _extract_line_after(user_message, "Extracted slots:")
    missing = _extract_line_after(user_message, "Missing slots:")
    parts = []
    if original:
        parts.append(f"request={original}")
    if slots:
        parts.append(f"slots={slots}")
    if missing:
        parts.append(f"missing={missing}")
    compact = "; ".join(parts) or " ".join(user_message.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _extract_line_after(text: str, marker: str) -> str:
    index = text.find(marker)
    if index < 0:
        return ""
    after = text[index + len(marker):].strip()
    return after.splitlines()[0].strip()
