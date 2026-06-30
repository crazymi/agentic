from __future__ import annotations

from dataclasses import dataclass

from agentic.runtime.events import InboundMessage, record_channel_message
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class ChannelResponse:
    ok: bool
    text: str
    error_type: str | None = None
    error_message: str | None = None


class ChannelLoop:
    def __init__(self, runtime: FullLoopRuntime, trace: TraceLogger):
        self.runtime = runtime
        self.trace = trace

    def handle_message(self, message: InboundMessage) -> ChannelResponse:
        record_channel_message(self.trace, message)
        if not message.text.strip():
            response = ChannelResponse(
                ok=False,
                text="Message must not be empty.",
                error_type="empty_message",
                error_message="message must not be empty",
            )
            self._record_response(response)
            return response
        try:
            result = self.runtime.run_user_message(message.text)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            response = ChannelResponse(
                ok=False,
                text=f"Failed: {exc}",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            self._record_response(response)
            return response
        response = ChannelResponse(
            ok=result.ok,
            text=result.final_answer,
            error_type=result.error_type,
            error_message=result.error_message,
        )
        self._record_response(response)
        return response

    def _record_response(self, response: ChannelResponse) -> None:
        self.trace.record(
            "channel_response_sent",
            {
                "ok": response.ok,
                "text": response.text,
                "error_type": response.error_type,
                "error_message": response.error_message,
            },
        )
