from __future__ import annotations

from dataclasses import dataclass

from agentic.artifacts.models import ArtifactKind, ArtifactRecord, ArtifactStatus
from agentic.artifacts.store import ArtifactStore


@dataclass(frozen=True)
class ArtifactAdmissionResult:
    artifact_id: str
    allowed: bool
    requires_approval: bool
    reason: str

    def to_record(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
        }


class ArtifactAdmissionService:
    def __init__(self, store: ArtifactStore):
        self.store = store

    def submit_for_review(self, artifact: ArtifactRecord) -> ArtifactRecord:
        status = (
            ArtifactStatus.REVIEW_REQUIRED
            if artifact.kind in {ArtifactKind.SCRIPT, ArtifactKind.CONFIG}
            else ArtifactStatus.DRAFT
        )
        return self.store.create(
            ArtifactRecord.from_record({**artifact.to_record(), "status": status.value})
        )

    def dry_run(self, artifact_id: str) -> ArtifactAdmissionResult:
        artifact = self.store.get(artifact_id)
        if artifact.kind != ArtifactKind.SCRIPT:
            return ArtifactAdmissionResult(
                artifact_id=artifact_id,
                allowed=True,
                requires_approval=False,
                reason="non-script artifact has no execution dry-run",
            )
        if artifact.status != ArtifactStatus.APPROVED:
            return ArtifactAdmissionResult(
                artifact_id=artifact_id,
                allowed=False,
                requires_approval=True,
                reason="script artifact must be approved before dry-run or execution",
            )
        return ArtifactAdmissionResult(
            artifact_id=artifact_id,
            allowed=True,
            requires_approval=False,
            reason="script artifact approved for dry-run planning; no code was executed",
        )

    def approve(self, artifact_id: str) -> ArtifactRecord:
        artifact = self.store.get(artifact_id)
        if artifact.kind not in {ArtifactKind.SCRIPT, ArtifactKind.CONFIG}:
            return self.store.transition(artifact_id, ArtifactStatus.APPROVED)
        if artifact.status != ArtifactStatus.REVIEW_REQUIRED:
            raise ValueError("artifact must be in review_required before approval")
        return self.store.transition(artifact_id, ArtifactStatus.APPROVED)

    def activate(self, artifact_id: str) -> ArtifactRecord:
        artifact = self.store.get(artifact_id)
        if artifact.kind in {ArtifactKind.SCRIPT, ArtifactKind.CONFIG} and artifact.status != ArtifactStatus.APPROVED:
            raise ValueError("executable/config artifact must be approved before activation")
        return self.store.transition(artifact_id, ArtifactStatus.ACTIVE)
