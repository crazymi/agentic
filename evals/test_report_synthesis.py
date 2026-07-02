from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from agentic.artifacts import ArtifactKind, ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.synthesis.report import (
    ReportInsight,
    ReportSynthesisResult,
    parse_synthesis_text,
)
from agentic.workflow_kernel import (
    StepType,
    WorkflowBuilder,
    WorkflowInterpreter,
    WorkflowStatus,
    WorkflowStore,
)
from agentic.workflow_kernel.models import WorkflowSpec, WorkflowStep


class FakeSynthesizer:
    def synthesize(
        self,
        *,
        spec: WorkflowSpec,
        items: list[dict[str, Any]],
        analyze: dict[str, Any],
    ) -> ReportSynthesisResult:
        return ReportSynthesisResult(
            ok=True,
            mode="model",
            model_id="fake-model",
            insights=[
                ReportInsight(
                    claim="AI 반도체와 환율 이슈가 동시에 반복되며 위험 선호 변화를 시사한다.",
                    evidence_ids=[1, 2],
                    implication="다음 수집 창에서 같은 주제가 반복되는지 확인한다.",
                    confidence="medium",
                ),
                ReportInsight(
                    claim="투자 심리 변화 언급이 기술주 변동성 관찰과 함께 나타난다.",
                    evidence_ids=[2, 3],
                    implication="관찰 키워드를 유지하되 단일 게시글만으로 판단하지 않는다.",
                    confidence="low",
                ),
            ],
            text='{"insights":[]}',
            evidence_count=3,
        )


class ReportSynthesisTests(unittest.TestCase):
    def test_parse_synthesis_text_requires_grounded_evidence_ids(self) -> None:
        result = parse_synthesis_text(
            """
            {"insights":[
              {"claim":"AI 반도체 수요와 기술주 위험 선호가 같이 언급된다.","evidence_ids":[1,2],"implication":"다음 창에서 반복 여부를 본다.","confidence":"medium"},
              {"claim":"근거 없는 일반론은 제거되어야 한다.","evidence_ids":[]}
            ]}
            """,
            evidence_count=3,
            min_insights=1,
        )

        self.assertTrue(result.ok, result.to_record())
        self.assertEqual(len(result.insights), 1)
        self.assertEqual(result.insights[0].evidence_ids, [1, 2])

    def test_parse_synthesis_text_handles_master_answer_wrapper(self) -> None:
        result = parse_synthesis_text(
            '{"decision":"answer","answer":"{\\"insights\\":[{\\"claim\\":\\"AI와 환율 신호가 같이 등장한다\\",\\"evidence_ids\\":[1,2],\\"implication\\":\\"다음 창에서 반복 여부 확인\\",\\"confidence\\":\\"medium\\"}]}"}',
            evidence_count=3,
            min_insights=1,
        )

        self.assertTrue(result.ok, result.to_record())
        self.assertEqual(result.insights[0].claim, "AI와 환율 신호가 같이 등장한다")

    def test_parse_synthesis_text_recovers_claim_blocks_without_exposing_raw_reasoning(self) -> None:
        result = parse_synthesis_text(
            """
            *   Claim: AI 반도체 수요가 강력함.
            *   Evidence_ids: [1]
            *   Implication: AI 관련 기술주 기대감이 유지될 수 있음.
            *   Confidence: high

            *   Claim: 환율 변동성과 기술주 간의 관계가 논의되고 있음.
            *   Evidence ID: [2]
            *   Implication: 환율 변동이 기술주 투자 심리에 영향을 미칠 수 있음.
            *   Confidence: medium
            """,
            evidence_count=3,
            min_insights=2,
        )

        self.assertTrue(result.ok, result.to_record())
        self.assertEqual([item.evidence_ids for item in result.insights], [[1], [2]])

    def test_parse_synthesis_text_filters_prompt_meta_and_cleans_embedded_claims(self) -> None:
        result = parse_synthesis_text(
            """
            Claim: Goal: Extract 2-3 repetitive themes/investment sentiment signals based only on the provided evidence.
            Evidence_ids: [2, 3]
            Confidence: medium

            Claim: Political instability and extreme right-wing sentiment (Evidence [1], [2]). Claim: 극우 성향 및 정치적 갈등 고조 (저신호).
            Evidence_ids: [1, 2]
            Confidence: medium
            """,
            evidence_count=3,
            min_insights=1,
        )

        self.assertTrue(result.ok, result.to_record())
        self.assertEqual(len(result.insights), 1)
        self.assertEqual(result.insights[0].claim, "극우 성향 및 정치적 갈등 고조 (저신호)")
        self.assertEqual(result.insights[0].evidence_ids, [1, 2])

    def test_interpreter_persists_model_assisted_insights_in_report_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "items.jsonl"
            source_file.write_text(
                "\n".join(
                    [
                        '{"uri":"local://1","title":"AI 반도체 수요","content_text":"AI 반도체 수요가 강하다는 의견"}',
                        '{"uri":"local://2","title":"환율과 기술주","content_text":"환율과 기술주 변동성 토론"}',
                        '{"uri":"local://3","title":"투자 심리 변화","content_text":"미국 주식 투자 심리 변화 관찰"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            workflow_store = WorkflowStore(root / "workflows.sqlite3")
            artifact_store = ArtifactStore(root / "artifacts.sqlite3")
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Local items",
                    locator=source_file.as_uri(),
                    enabled=True,
                    metadata={"quality": {"min_items": 3, "min_score": 70}},
                )
            )
            spec = workflow_store.create_spec(_spec(source.source_id))
            workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.PROPOSED)
            spec = workflow_store.transition_spec(spec.workflow_id, WorkflowStatus.APPROVED)

            result = WorkflowBuilder(
                WorkflowInterpreter(
                    workflow_store=workflow_store,
                    artifact_store=artifact_store,
                    source_runtime=SourceRuntime(source_store=source_store, resource_store=resource_store),
                    resource_store=resource_store,
                    report_synthesizer=FakeSynthesizer(),
                )
            ).run_approved(spec)
            artifacts = artifact_store.list(kind=ArtifactKind.REPORT, run_id=result.run.run_id)

        self.assertTrue(result.ok)
        self.assertEqual(len(artifacts), 1)
        self.assertIn("## Model-Assisted Insights", artifacts[0].content)
        self.assertTrue(artifacts[0].metadata["report_synthesis"]["ok"])
        self.assertEqual(artifacts[0].metadata["report_synthesis"]["model_id"], "fake-model")


def _spec(source_id: str) -> WorkflowSpec:
    return WorkflowSpec(
        name="Synthesis workflow",
        goal="최근 커뮤니티 글에서 투자 심리 신호를 요약한다.",
        status=WorkflowStatus.PROPOSED,
        triggers=[{"type": "manual"}],
        sources=[{"source_id": source_id, "kind": SourceKind.LOCAL_FILE.value}],
        outputs=[{"kind": "report"}],
        success_criteria=["Report includes grounded synthesis."],
        steps=[
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect",
                config={"source_id": source_id, "source": SourceKind.LOCAL_FILE.value},
            ),
            WorkflowStep(step_id="analyze", step_type=StepType.ANALYZE, name="Analyze"),
            WorkflowStep(step_id="report", step_type=StepType.REPORT, name="Report"),
        ],
    )


if __name__ == "__main__":
    unittest.main()
