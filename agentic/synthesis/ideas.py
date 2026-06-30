from __future__ import annotations

from agentic.memory.models import MemoryKind
from agentic.memory.store import MemoryStore


def synthesize_ideas(store: MemoryStore, *, query: str = "") -> dict:
    ideas = store.search(query, kind=MemoryKind.IDEA, limit=20) if query else store.search(kind=MemoryKind.IDEA, limit=20)
    tags = sorted({tag for idea in ideas for tag in idea.tags})
    insight = "No ideas available." if not ideas else (
        f"Found {len(ideas)} related ideas. Shared tags: {', '.join(tags) or 'none'}."
    )
    record = store.add(
        kind=MemoryKind.INSIGHT,
        text=insight,
        tags=["synthesis", *tags[:5]],
        source="agentic",
        links=[idea.memory_id for idea in ideas],
    )
    return {"insight": record.text, "memory_id": record.memory_id, "source_count": len(ideas)}
