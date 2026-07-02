from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic.agents.master import MasterAgent
from agentic.config.settings import AppConfig
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.runtime.subagent_loop import SubagentLoop, SubagentLoopResult
from agentic.runtime.turn import MasterDecision, MasterTurn
from agentic.skills.loader import SkillLoader
from agentic.skills.registry import SkillRegistry
from agentic.tasks.ledger import TaskLedger
from agentic.tasks.subagent_task import SubAgentTask
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class FullLoopResult:
    ok: bool
    final_answer: str
    decision: MasterDecision
    task: SubAgentTask | None = None
    subagent_result: SubagentLoopResult | None = None
    error_type: str | None = None
    error_message: str | None = None
    trace_path: Path | None = None


class FullLoopRuntime:
    def __init__(
        self,
        *,
        master_turn: MasterTurn,
        subagent_loop: SubagentLoop,
        ledger: TaskLedger,
        trace: TraceLogger,
    ):
        self.master_turn = master_turn
        self.subagent_loop = subagent_loop
        self.ledger = ledger
        self.trace = trace

    @classmethod
    def from_config(
        cls,
        config: AppConfig,
        *,
        state_dir: str | Path | None = None,
    ) -> "FullLoopRuntime":
        prompt_builder = PromptBuilder.from_files(
            config.prompts.master,
            config.prompts.subagent,
            config.prompts.tool_call_grammar,
        )
        trace = TraceLogger(config.runtime.trace_file)
        master_provider = LocalGGUFProvider(config.model(config.runtime.default_master_model))
        subagent_provider = LocalGGUFProvider(config.model(config.runtime.default_subagent_model))
        tools = ToolRegistry.with_defaults(state_dir=state_dir)
        skills = SkillRegistry(
            SkillLoader(config.root / "skills").load_all(),
            tools=tools,
        )

        return cls(
            master_turn=MasterTurn(
                MasterAgent(
                    provider=master_provider,
                    prompt_builder=prompt_builder,
                    skills=skills,
                ),
                trace=trace,
            ),
            subagent_loop=SubagentLoop(
                provider=subagent_provider,
                prompt_builder=prompt_builder,
                tools=tools,
                skills=skills,
                trace=trace,
            ),
            ledger=TaskLedger(trace=trace),
            trace=trace,
        )

    def run(self, message: str) -> FullLoopResult:
        return self.run_user_message(message)

    def run_user_message(self, message: str) -> FullLoopResult:
        cleaned_message = message.strip()
        if not cleaned_message:
            raise ValueError("message must not be empty")

        self.trace.record("user_message_received", {"message": cleaned_message})
        decision = self.master_turn.decide(cleaned_message)

        if decision.action == "answer":
            answer = decision.answer or ""
            self._record_final(answer, decision=decision)
            return FullLoopResult(
                ok=True,
                final_answer=answer,
                decision=decision,
                trace_path=self.trace.path,
            )

        if not decision.task:
            return self._failure(
                decision=decision,
                error_type="missing_delegation_task",
                error_message="master delegated without a task",
            )

        task = self.ledger.create_task(decision.task)
        subagent_result = self.subagent_loop.run_once(task)
        if not subagent_result.ok:
            return self._failure(
                decision=decision,
                task=task,
                subagent_result=subagent_result,
                error_type=subagent_result.error_type or "subagent_failed",
                error_message=subagent_result.error_message or "subagent failed",
            )

        answer = subagent_result.report or task.result or ""
        self._record_final(answer, decision=decision, task=task)
        return FullLoopResult(
            ok=True,
            final_answer=answer,
            decision=decision,
            task=task,
            subagent_result=subagent_result,
            trace_path=self.trace.path,
        )

    def _failure(
        self,
        *,
        decision: MasterDecision,
        error_type: str,
        error_message: str,
        task: SubAgentTask | None = None,
        subagent_result: SubagentLoopResult | None = None,
    ) -> FullLoopResult:
        final_answer = f"Failed: {error_message}"
        self._record_final(
            final_answer,
            decision=decision,
            task=task,
            ok=False,
            error_type=error_type,
            error_message=error_message,
        )
        return FullLoopResult(
            ok=False,
            final_answer=final_answer,
            decision=decision,
            task=task,
            subagent_result=subagent_result,
            error_type=error_type,
            error_message=error_message,
            trace_path=self.trace.path,
        )

    def _record_final(
        self,
        answer: str,
        *,
        decision: MasterDecision,
        task: SubAgentTask | None = None,
        ok: bool = True,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        payload = {
            "ok": ok,
            "answer": answer,
            "decision": decision.action,
        }
        if task is not None:
            payload["task_id"] = task.task_id
            payload["task_state"] = task.state.value
        if error_type is not None:
            payload["error_type"] = error_type
        if error_message is not None:
            payload["error_message"] = error_message
        self.trace.record("master_final_answer", payload)
