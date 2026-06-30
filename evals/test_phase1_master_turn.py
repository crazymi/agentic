from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.agents.master import MasterAgent
from agentic.models.local_gguf import ModelResponse
from agentic.prompts.builder import PromptBuilder
from agentic.runtime.turn import MasterDecision, MasterTurn
from agentic.traces.logger import TraceLogger


class FakeMasterProvider:
    def __init__(self, text: str):
        self.text = text
        self.config = type("Config", (), {"system_prompt": ""})()

    def generate(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            text=self.text,
            command=("fake-master",),
            returncode=0,
            raw_text=self.text,
            meta={"role": "master"},
        )


class Phase1MasterTurnTests(unittest.TestCase):
    def test_master_decision_parses_answer(self) -> None:
        decision = MasterDecision.parse('{"action":"answer","answer":"2"}')

        self.assertEqual(decision.action, "answer")
        self.assertEqual(decision.answer, "2")
        self.assertIsNone(decision.task)

    def test_master_decision_parses_delegate(self) -> None:
        decision = MasterDecision.parse(
            '{"action":"delegate","task":"Use add tool to compute 1+1."}'
        )

        self.assertEqual(decision.action, "delegate")
        self.assertEqual(decision.task, "Use add tool to compute 1+1.")
        self.assertIsNone(decision.answer)

    def test_master_turn_uses_structured_model_decision(self) -> None:
        turn = MasterTurn(_fake_agent('{"action":"answer","answer":"hello"}'))

        decision = turn.decide("Say hello.")

        self.assertEqual(decision.action, "answer")
        self.assertEqual(decision.answer, "hello")

    def test_master_turn_delegates_simple_addition(self) -> None:
        turn = MasterTurn(_fake_agent("unstructured model output"))

        decision = turn.decide("1+1은 뭐지?")

        self.assertEqual(decision.action, "delegate")
        self.assertEqual(decision.task, "Use add tool to compute 1+1.")

    def test_master_turn_records_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            turn = MasterTurn(_fake_agent("plain answer"), trace=trace)

            decision = turn.decide("What is your status?")
            events = trace.read_events()

        self.assertEqual(decision.action, "answer")
        self.assertEqual(
            [event.event_type for event in events],
            ["master_model_called", "master_delegation_decision"],
        )
        self.assertEqual(events[0].payload["message"], "What is your status?")
        self.assertEqual(events[1].payload["action"], "answer")


def _fake_agent(text: str) -> MasterAgent:
    return MasterAgent(
        provider=FakeMasterProvider(text),  # type: ignore[arg-type]
        prompt_builder=PromptBuilder(),
    )


if __name__ == "__main__":
    unittest.main()
