from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from agentic.artifacts import ArtifactRecord
from agentic.sources import SourceDefinition
from agentic.workflow_kernel import WorkflowSpec


class WorkflowProbeKind(StrEnum):
    NEWSLETTER = "newsletter"
    SOCIAL_TREND = "social_trend"
    IDEA_SYNTHESIS = "idea_synthesis"
    BROWSER_WATCHER = "browser_watcher"
    CODING = "coding"


@dataclass(frozen=True)
class WorkflowProbe:
    kind: WorkflowProbeKind
    request: str
    spec: WorkflowSpec
    sources: list[SourceDefinition] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)

    def to_record(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "request": self.request,
            "workflow": self.spec.to_record(),
            "sources": [source.to_record() for source in self.sources],
            "artifacts": [artifact.to_record() for artifact in self.artifacts],
        }
