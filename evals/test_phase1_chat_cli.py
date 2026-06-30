from __future__ import annotations

import unittest
from dataclasses import dataclass

from agentic.app.chat import run_chat_once, run_chat_repl


@dataclass
class FakeResult:
    final_answer: str


class FakeRuntime:
    def __init__(self, answer: object):
        self.answer = answer
        self.messages: list[str] = []

    def run(self, message: str) -> object:
        self.messages.append(message)
        return self.answer


class Phase1ChatCliTests(unittest.TestCase):
    def test_run_chat_once_returns_fake_runtime_answer(self) -> None:
        runtime = FakeRuntime(FakeResult("2"))

        answer = run_chat_once(config=None, message=" 1+1은 뭐지? ", runtime=runtime)  # type: ignore[arg-type]

        self.assertEqual(answer, "2")
        self.assertEqual(runtime.messages, ["1+1은 뭐지?"])

    def test_run_chat_once_accepts_string_runtime_result(self) -> None:
        runtime = FakeRuntime("direct answer")

        answer = run_chat_once(config=None, message="hello", runtime=runtime)  # type: ignore[arg-type]

        self.assertEqual(answer, "direct answer")

    def test_run_chat_once_requires_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "message"):
            run_chat_once(config=None, message=" ", runtime=FakeRuntime("unused"))  # type: ignore[arg-type]

    def test_run_chat_once_uses_runtime_factory(self) -> None:
        runtimes: list[FakeRuntime] = []

        def factory(config: object) -> FakeRuntime:
            runtime = FakeRuntime(FakeResult(f"config={config}"))
            runtimes.append(runtime)
            return runtime

        answer = run_chat_once(config="fake-config", message="hello", runtime_factory=factory)  # type: ignore[arg-type]

        self.assertEqual(answer, "config=fake-config")
        self.assertEqual(len(runtimes), 1)
        self.assertEqual(runtimes[0].messages, ["hello"])

    def test_repl_reuses_runtime_until_quit(self) -> None:
        runtime = FakeRuntime("ok")
        prompts: list[str] = []
        outputs: list[str] = []
        inputs = iter(["first", "second", "quit"])

        def input_func(prompt: str) -> str:
            prompts.append(prompt)
            return next(inputs)

        run_chat_repl(
            config=None,  # type: ignore[arg-type]
            runtime_factory=lambda config: runtime,
            input_func=input_func,
            output_func=outputs.append,
            prompt="> ",
        )

        self.assertEqual(prompts, ["> ", "> ", "> "])
        self.assertEqual(outputs, ["ok", "ok"])
        self.assertEqual(runtime.messages, ["first", "second"])


if __name__ == "__main__":
    unittest.main()
