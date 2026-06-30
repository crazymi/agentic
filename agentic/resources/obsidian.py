from __future__ import annotations

from pathlib import Path

from agentic.memory.models import MemoryRecord


class ObsidianLocalConnector:
    connector_id = "obsidian-local"

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def write_memory_note(self, memory: MemoryRecord) -> Path:
        filename = f"{memory.memory_id}.md"
        path = self.vault_path / filename
        tags = " ".join(f"#{tag}" for tag in memory.tags)
        path.write_text(
            f"# {memory.kind.value}: {memory.memory_id}\n\n"
            f"{memory.text}\n\n"
            f"{tags}\n\n"
            f"source: {memory.source}\n",
            encoding="utf-8",
        )
        return path
