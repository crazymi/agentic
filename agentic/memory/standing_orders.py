from __future__ import annotations

from agentic.memory.models import MemoryKind
from agentic.memory.store import MemoryStore


def add_standing_goal(store: MemoryStore, text: str, *, tags: list[str] | None = None):
    return store.add(
        kind=MemoryKind.STANDING_GOAL,
        text=text,
        tags=tags or ["standing_goal"],
        source="user",
    )


def standing_goal_prompt_context(store: MemoryStore) -> str:
    goals = store.standing_goals()
    if not goals:
        return ""
    lines = ["Standing goals:"]
    lines.extend(f"- {goal.text}" for goal in goals)
    return "\n".join(lines)
