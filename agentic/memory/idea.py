from __future__ import annotations

from dataclasses import dataclass

from agentic.memory.models import MemoryKind, MemoryRecord
from agentic.memory.store import MemoryStore


@dataclass(frozen=True)
class IdeaCaptureResult:
    memory: MemoryRecord
    followup_question: MemoryRecord


def capture_idea(store: MemoryStore, text: str, *, source: str = "chat") -> IdeaCaptureResult:
    tags = _infer_tags(text)
    memory = store.add(kind=MemoryKind.IDEA, text=text.strip(), tags=tags, source=source)
    question = store.add(
        kind=MemoryKind.FOLLOWUP_QUESTION,
        text=f"What context or concrete next step matters most for this idea: {text.strip()}?",
        tags=tags,
        source="agentic",
        links=[memory.memory_id],
    )
    return IdeaCaptureResult(memory=memory, followup_question=question)


def _infer_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags = []
    for keyword in ("startup", "agent", "memory", "browser", "finance", "뉴스", "아이디어"):
        if keyword in lowered:
            tags.append(keyword)
    return tags or ["idea"]
