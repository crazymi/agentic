from __future__ import annotations

from dataclasses import dataclass, field

from agentic.artifacts.models import ArtifactKind, ArtifactRecord
from agentic.artifacts.report_quality import evaluate_report_quality
from agentic.artifacts.store import ArtifactStore
from agentic.channels.ntfy import NtfyChannel
from agentic.delivery.models import DeliveryChannel, DeliveryRecord, DeliveryStatus
from agentic.delivery.store import DeliveryStore


@dataclass(frozen=True)
class DeliveryBatchResult:
    enqueued: list[DeliveryRecord] = field(default_factory=list)
    sent: list[DeliveryRecord] = field(default_factory=list)
    failed: list[DeliveryRecord] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_record(self) -> dict:
        return {
            "ok": self.ok,
            "enqueued": [record.to_record() for record in self.enqueued],
            "sent": [record.to_record() for record in self.sent],
            "failed": [record.to_record() for record in self.failed],
        }


class ReportDeliveryService:
    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        delivery_store: DeliveryStore,
        ntfy_channel: NtfyChannel | None = None,
        web_url: str = "http://127.0.0.1:8765",
    ):
        self.artifact_store = artifact_store
        self.delivery_store = delivery_store
        self.ntfy_channel = ntfy_channel
        self.web_url = web_url

    def enqueue_report_artifacts(self, *, limit: int = 100) -> list[DeliveryRecord]:
        records: list[DeliveryRecord] = []
        for artifact in self.artifact_store.list(kind=ArtifactKind.REPORT, limit=limit):
            if not _report_quality_ok(artifact):
                continue
            existing = self.delivery_store.find_by_artifact_channel(
                artifact.artifact_id,
                DeliveryChannel.NTFY,
            )
            if existing is not None:
                continue
            records.append(self.delivery_store.create(self._delivery_for_artifact(artifact)))
        return records

    def deliver_pending(self, *, limit: int = 20, max_attempts: int = 3) -> DeliveryBatchResult:
        sent: list[DeliveryRecord] = []
        failed: list[DeliveryRecord] = []
        if self.ntfy_channel is None:
            return DeliveryBatchResult()
        candidates = self.delivery_store.list(
            status=DeliveryStatus.PENDING,
            channel=DeliveryChannel.NTFY,
            limit=limit,
        )
        if len(candidates) < limit:
            candidates.extend(
                delivery
                for delivery in self.delivery_store.list(
                    status=DeliveryStatus.FAILED,
                    channel=DeliveryChannel.NTFY,
                    limit=limit - len(candidates),
                )
                if delivery.attempts < max_attempts
            )
        for delivery in candidates[:limit]:
            if self.ntfy_channel.send_text(
                title=delivery.title,
                body=delivery.body,
                tags="bar_chart",
            ):
                sent.append(self.delivery_store.mark_sent(delivery.delivery_id))
            else:
                failed.append(
                    self.delivery_store.mark_failed(
                        delivery.delivery_id,
                        {"type": "send_failed", "message": "ntfy send returned false"},
                    )
                )
        return DeliveryBatchResult(sent=sent, failed=failed)

    def enqueue_and_deliver_reports(
        self,
        *,
        enqueue_limit: int = 100,
        deliver_limit: int = 20,
    ) -> DeliveryBatchResult:
        enqueued = self.enqueue_report_artifacts(limit=enqueue_limit)
        delivered = self.deliver_pending(limit=deliver_limit)
        return DeliveryBatchResult(
            enqueued=enqueued,
            sent=delivered.sent,
            failed=delivered.failed,
        )

    def _delivery_for_artifact(self, artifact: ArtifactRecord) -> DeliveryRecord:
        preview = _preview(artifact.content)
        body_lines = [
            f"{artifact.name}",
            preview,
            f"artifact={artifact.artifact_id}",
        ]
        if artifact.workflow_id:
            body_lines.append(f"workflow={artifact.workflow_id}")
        if self.web_url:
            body_lines.append(self.web_url.rstrip("/"))
        return DeliveryRecord(
            artifact_id=artifact.artifact_id,
            channel=DeliveryChannel.NTFY,
            destination="ntfy",
            title="Agentic report ready",
            body="\n".join(line for line in body_lines if line),
        )


def _preview(text: str, *, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _report_quality_ok(artifact: ArtifactRecord) -> bool:
    metadata = artifact.metadata or {}
    quality = metadata.get("report_quality")
    if isinstance(quality, dict) and "ok" in quality:
        return bool(quality.get("ok")) and _report_synthesis_ok(metadata)
    return evaluate_report_quality(artifact.content).ok and _report_synthesis_ok(metadata)


def _report_synthesis_ok(metadata: dict) -> bool:
    synthesis = metadata.get("report_synthesis")
    if synthesis is None:
        return True
    if not isinstance(synthesis, dict):
        return False
    return bool(synthesis.get("ok"))
