from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic.config.settings import AppConfig
from agentic.probes.harness import (
    DEFAULT_PROBE_ANSWERS,
    DEFAULT_PROBE_REQUEST,
    run_workflow_builder_probe,
    run_workflow_spec_probe,
)
from agentic.runtime.worker import TaskExecutionContext
from agentic.tasks.state_machine import TaskRecord


WORKFLOW_BUILDER_PROBE_TASK_KIND = "workflow_builder_probe"
WORKFLOW_SPEC_PROBE_TASK_KIND = "workflow_spec_probe"


@dataclass(frozen=True)
class WorkflowBuilderProbeExecutor:
    config: AppConfig
    state_dir: Path | None = None

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        context.heartbeat(task.task_id)
        context.raise_if_cancelled(task.task_id)
        request = str(task.input.get("request") or DEFAULT_PROBE_REQUEST)
        raw_answers = task.input.get("answers")
        answers = (
            [str(answer) for answer in raw_answers]
            if isinstance(raw_answers, list) and raw_answers
            else list(DEFAULT_PROBE_ANSWERS)
        )
        result = run_workflow_builder_probe(
            self.config,
            request=request,
            answers=answers,
            state_dir=task.input.get("state_dir") or self.state_dir,
        )
        context.raise_if_cancelled(task.task_id)
        record = result.to_record()
        if not result.ok:
            raise RuntimeError(result.blocker or "workflow builder probe did not pass")
        return record


@dataclass(frozen=True)
class WorkflowSpecProbeExecutor:
    config: AppConfig
    state_dir: Path | None = None

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        context.heartbeat(task.task_id)
        context.raise_if_cancelled(task.task_id)
        request = str(task.input.get("request") or DEFAULT_PROBE_REQUEST)
        raw_answers = task.input.get("answers")
        answers = (
            [str(answer) for answer in raw_answers]
            if isinstance(raw_answers, list) and raw_answers
            else list(DEFAULT_PROBE_ANSWERS)
        )
        result = run_workflow_spec_probe(
            self.config,
            request=request,
            answers=answers,
            state_dir=task.input.get("state_dir") or self.state_dir,
        )
        context.raise_if_cancelled(task.task_id)
        record = result.to_record()
        if not result.ok:
            raise RuntimeError(result.blocker or "workflow spec probe did not pass")
        return record
