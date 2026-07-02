from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from agentic.runtime.worker import TaskExecutionContext, TaskExecutor
from agentic.tasks.state_machine import TaskRecord


@dataclass(frozen=True)
class TaskRouter:
    executors: Mapping[str, TaskExecutor]

    def execute(self, task: TaskRecord, context: TaskExecutionContext) -> dict:
        try:
            executor = self.executors[task.kind]
        except KeyError as exc:
            known = ", ".join(sorted(self.executors))
            raise ValueError(
                f"no executor registered for task kind '{task.kind}'. Known kinds: {known}"
            ) from exc
        return executor.execute(task, context)
