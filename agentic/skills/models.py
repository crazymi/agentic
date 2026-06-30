from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SkillRequirements:
    connectors: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillTriggers:
    keywords: list[str] = field(default_factory=list)
    task_kinds: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    requires: SkillRequirements = field(default_factory=SkillRequirements)
    triggers: SkillTriggers = field(default_factory=SkillTriggers)
    enabled: bool = True


@dataclass(frozen=True)
class SkillPackage:
    path: Path
    manifest: SkillManifest
    body: str

    @property
    def name(self) -> str:
        return self.manifest.name
