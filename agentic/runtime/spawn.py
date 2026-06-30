from __future__ import annotations

from dataclasses import dataclass

from agentic.tasks.subagent_task import SubAgentTask


@dataclass(frozen=True)
class SpawnedSubAgent:
    task: SubAgentTask
    simulated: bool = True


def simulate_subagent_spawn(task: SubAgentTask) -> SpawnedSubAgent:
    return SpawnedSubAgent(task=task)
