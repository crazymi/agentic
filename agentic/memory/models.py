from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from agentic.tasks.state_machine import utc_now


class MemoryKind(StrEnum):
    IDEA = "idea"
    PREFERENCE = "preference"
    STANDING_GOAL = "standing_goal"
    FOLLOWUP_QUESTION = "followup_question"
    INSIGHT = "insight"


def memory_id() -> str:
    return f"mem_{uuid4().hex}"


@dataclass(frozen=True)
class MemoryRecord:
    kind: MemoryKind
    text: str
    tags: list[str] = field(default_factory=list)
    source: str = "local"
    links: list[str] = field(default_factory=list)
    memory_id: str = field(default_factory=memory_id)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", MemoryKind(self.kind))
        if not self.text:
            raise ValueError("memory text must not be empty")
