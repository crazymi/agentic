from __future__ import annotations

import unittest

from agentic.models.response_sanitizer import sanitize_model_output


class ResponseSanitizerTests(unittest.TestCase):
    def test_plain_text_is_preserved(self) -> None:
        self.assertEqual(sanitize_model_output("hello"), "hello")

    def test_final_channel_is_extracted(self) -> None:
        raw = "<|channel>thought\nthinking<channel|>한국의 수도는 서울입니다. [end of text]"

        self.assertEqual(sanitize_model_output(raw), "한국의 수도는 서울입니다.")

    def test_diffusion_timing_lines_are_dropped(self) -> None:
        raw = "\n".join(
            [
                "<|channel>thought",
                "thinking",
                "<channel|>{\"tool\":\"add\",\"arguments\":{\"a\":1,\"b\":1}}",
                "total time: 841.93ms",
                "throughput: 304.1 tok/s",
            ]
        )

        self.assertEqual(
            sanitize_model_output(raw),
            '{"tool":"add","arguments":{"a":1,"b":1}}',
        )


if __name__ == "__main__":
    unittest.main()
