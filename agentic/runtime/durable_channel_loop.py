from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agentic.runtime.events import InboundMessage, record_channel_message
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.runtime.task_pool import TaskPool
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import TaskRecord
from agentic.tasks.store import TaskStore
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class DurableChannelResponse:
    ok: bool
    task_id: str
    text: str


class DurableChannelLoop:
    def __init__(
        self,
        *,
        store: TaskStore,
        pool: TaskPool,
        trace: TraceLogger,
    ):
        self.store = store
        self.pool = pool
        self.trace = trace

    def handle_message(self, message: InboundMessage) -> DurableChannelResponse:
        record_channel_message(self.trace, message)
        task = self.store.create_task(
            kind="chat_turn",
            input={
                "message": message.text,
                "channel": message.channel,
                "message_id": message.message_id,
                "user_id": message.user_id,
            },
        )
        self.trace.record(
            "task_enqueued",
            {"task_id": task.task_id, "kind": task.kind, "message_id": message.message_id},
        )
        self.pool.kick()
        return DurableChannelResponse(
            ok=True,
            task_id=task.task_id,
            text=f"Task queued: {task.task_id}",
        )


class ChatTurnExecutor:
    def __init__(self, runtime_factory: Callable[[], FullLoopRuntime]):
        self.runtime_factory = runtime_factory

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        context.heartbeat(task.task_id)
        context.raise_if_cancelled(task.task_id)
        message = str(task.input.get("message", "")).strip()
        if not message:
            raise ValueError("chat_turn task message must not be empty")
        result = self.runtime_factory().run_user_message(message)
        context.raise_if_cancelled(task.task_id)
        return {
            "ok": result.ok,
            "final_answer": result.final_answer,
            "error_type": result.error_type,
            "error_message": result.error_message,
        }
