from __future__ import annotations

import unittest

from agentic.models.response_sanitizer import sanitize_user_facing_answer
from agentic.models.local_gguf import ModelResponse
from agentic.runtime.turn import MasterTurn


class FakeAgent:
    def __init__(self, text: str):
        self.text = text

    def generate(self, user_message: str) -> ModelResponse:
        return ModelResponse(
            text=self.text,
            raw_text=self.text,
            command=("fake",),
            returncode=0,
        )


class Milestone3QualityFixTests(unittest.TestCase):
    def test_thought_channel_is_not_user_facing(self) -> None:
        raw = "<|channel>thought\nprivate reasoning\n<|channel>final\nhello"

        self.assertEqual(sanitize_user_facing_answer(raw), "hello")

    def test_json_answer_is_extracted(self) -> None:
        raw = '{"decision":"answer","answer":"안녕하세요!"}'

        self.assertEqual(sanitize_user_facing_answer(raw), "안녕하세요!")

    def test_partial_decision_fragment_is_not_answer(self) -> None:
        raw = '{"decision":"answer","answer":"안녕하세요!'

        self.assertEqual(sanitize_user_facing_answer(raw), "")

    def test_master_fallback_uses_clean_answer(self) -> None:
        turn = MasterTurn(FakeAgent("<|channel>thought\nhidden\n<|channel>final\nclean"))

        decision = turn.decide("hello")

        self.assertEqual(decision.answer, "clean")

    def test_addition_still_delegates(self) -> None:
        turn = MasterTurn(FakeAgent("<|channel>thought\nhidden"))

        decision = turn.decide("1+1은?")

        self.assertEqual(decision.action, "delegate")


if __name__ == "__main__":
    unittest.main()
