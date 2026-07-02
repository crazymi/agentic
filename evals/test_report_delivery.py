from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactRecord, ArtifactStore
from agentic.delivery import DeliveryChannel, DeliveryStatus, DeliveryStore, ReportDeliveryService


class FakeNtfy:
    def __init__(self, results: list[bool] | None = None):
        self.messages: list[dict] = []
        self.results = list(results or [True])

    def send_text(self, *, title: str, body: str, tags: str = "") -> bool:
        self.messages.append({"title": title, "body": body, "tags": tags})
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]


class ReportDeliveryTests(unittest.TestCase):
    def test_report_artifact_is_enqueued_and_sent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            ntfy = FakeNtfy()
            artifact = artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Hourly report",
                    content=_quality_report_body(),
                    workflow_id="wf_1",
                )
            )
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=ntfy,
                web_url="http://local",
            )

            result = service.enqueue_and_deliver_reports()

            self.assertTrue(result.ok)
            self.assertEqual(len(result.enqueued), 1)
            self.assertEqual(len(result.sent), 1)
            self.assertEqual(result.sent[0].status, DeliveryStatus.SENT)
            self.assertEqual(result.sent[0].artifact_id, artifact.artifact_id)
            self.assertIn("Executive Summary", ntfy.messages[0]["body"])

    def test_delivery_is_not_duplicated_for_same_artifact_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Report",
                    content=_quality_report_body(),
                )
            )
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=FakeNtfy(),
            )

            service.enqueue_and_deliver_reports()
            service.enqueue_and_deliver_reports()

            deliveries = delivery_store.list(channel=DeliveryChannel.NTFY)
            self.assertEqual(len(deliveries), 1)

    def test_low_quality_report_artifact_is_not_enqueued(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Too short",
                    content="trend report body",
                )
            )
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=FakeNtfy(),
            )

            result = service.enqueue_and_deliver_reports()

            self.assertEqual(result.enqueued, [])
            self.assertEqual(result.sent, [])
            self.assertEqual(delivery_store.list(channel=DeliveryChannel.NTFY), [])

    def test_failed_report_synthesis_is_not_enqueued(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Synthesis failed",
                    content=_quality_report_body(),
                    metadata={
                        "report_synthesis": {
                            "ok": False,
                            "mode": "model",
                            "model_id": "master-gemma-iq2",
                            "error": "insufficient_grounded_insights",
                        }
                    },
                )
            )
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=FakeNtfy(),
            )

            result = service.enqueue_and_deliver_reports()

            self.assertEqual(result.enqueued, [])
            self.assertEqual(result.sent, [])
            self.assertEqual(delivery_store.list(channel=DeliveryChannel.NTFY), [])

    def test_missing_ntfy_channel_keeps_delivery_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Report",
                    content=_quality_report_body(),
                )
            )
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=None,
            )

            result = service.enqueue_and_deliver_reports()

            self.assertTrue(result.ok)
            deliveries = delivery_store.list(channel=DeliveryChannel.NTFY)
            self.assertEqual(deliveries[0].status, DeliveryStatus.PENDING)

    def test_failed_delivery_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            delivery_store = DeliveryStore(root / "deliveries.sqlite3")
            artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name="Report",
                    content=_quality_report_body(),
                )
            )
            ntfy = FakeNtfy(results=[False, True])
            service = ReportDeliveryService(
                artifact_store=artifact_store,
                delivery_store=delivery_store,
                ntfy_channel=ntfy,
            )

            first = service.enqueue_and_deliver_reports()
            second = service.enqueue_and_deliver_reports()

            self.assertEqual(len(first.failed), 1)
            self.assertEqual(len(second.sent), 1)
            self.assertEqual(second.sent[0].status, DeliveryStatus.SENT)


def _quality_report_body() -> str:
    return """# Report

Goal: recurring signal monitoring

## Executive Summary

- Analyzed 3 item(s) for the requested recurring workflow.
- Top themes: AI, semiconductor, market, sentiment
- Evidence window: 3 item(s)

## Evidence

- [1] AI 반도체 수요 증가 | 투자자들이 AI 반도체 수요와 공급 부족을 논의함 | https://example.test/post-1
- [2] 미국 주식 심리 변화 | 위험 선호와 기술주 변동성에 대한 토론이 늘어남 | https://example.test/post-2
- [3] 환율과 성장주 압박 | 환율과 금리 이슈가 성장주 의견에 반복 등장 | https://example.test/post-3

## Signals

- AI 반도체 수요 증가 :: AI 반도체 수요와 공급 부족이 반복되는 관찰 포인트입니다.
- 미국 주식 심리 변화 :: 투자 심리 변화와 위험 선호가 함께 언급됩니다.
- 환율과 성장주 압박 :: 환율과 금리 단어가 성장주 토론 근처에 나타납니다.

## Source Quality

- source=src_example ok=True score=100 items=3 reasons=

## Next Watch Points

- Watch whether the same themes persist in the next run.
- Compare the next evidence window before treating a theme as durable.
- If source quality drops, require recovery before delivery.
"""


if __name__ == "__main__":
    unittest.main()
