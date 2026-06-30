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
        self._record("master_model_called", {"message": user_message})
        response = self.agent.generate(user_message)

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
        answer = sanitize_user_facing_answer(response.text)
        if not answer:
            answer = "답변을 정리하지 못했습니다."
        return MasterDecision.answer_directly(answer)

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
