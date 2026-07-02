from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.config.settings import load_app_config
from agentic.probes import run_workflow_builder_probe, run_workflow_spec_probe
from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore
from agentic.workflow_kernel import WorkflowSpec, WorkflowStatus, WorkflowStep, WorkflowStore


class ProposalRuntime:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.messages: list[str] = []

    def run(self, message: str) -> str:
        self.messages.append(message)
        service = SkillWorkshopService(
            SkillWorkshopStore(self.state_dir / "skill_workshop.sqlite3"),
            skills_root=self.state_dir / "skills",
        )
        proposal = service.propose_create(
            name="vague-workflow-handler",
            description="Guide vague workflow requests",
            proposal_body=VALID_PROPOSAL_BODY,
            source="probe-test",
        )
        return proposal.proposal_id


VALID_PROPOSAL_BODY = """# Vague Workflow Handler
- Trigger: User asks for automation or workflow design.
- Interview: Ask one missing question at a time.
- Discovery: Identify tools, connectors, storage, and policies.
- Proposal: Produce a workflow spec for user review.
- Approval: Gate risky or external actions before execution.
- Recording: Log outcomes and evidence after each run.
- Evolution: Propose skill updates from feedback and failures.
"""


class TruncatedProposalRuntime(ProposalRuntime):
    def run(self, message: str) -> str:
        self.messages.append(message)
        service = SkillWorkshopService(
            SkillWorkshopStore(self.state_dir / "skill_workshop.sqlite3"),
            skills_root=self.state_dir / "skills",
        )
        proposal = service.propose_create(
            name="vague-workflow-handler",
            description="Guide vague workflow requests",
            proposal_body="# Vague Workflow\n- **Trigger**: User asks.\n- **Proposal**: Pro",
            source="probe-test",
        )
        return proposal.proposal_id


class BoldLabelProposalRuntime(ProposalRuntime):
    def run(self, message: str) -> str:
        self.messages.append(message)
        service = SkillWorkshopService(
            SkillWorkshopStore(self.state_dir / "skill_workshop.sqlite3"),
            skills_root=self.state_dir / "skills",
        )
        proposal = service.propose_create(
            name="vague-workflow-handler",
            description="Guide vague workflow requests",
            proposal_body="""# Vague Workflow Handler
- **Trigger**: User asks for automation or workflow design.
- **Interview**: Ask one missing question at a time.
- **Discovery**: Identify tools, connectors, storage, and policies.
- **Proposal**: Produce a workflow spec for user review.
- **Approval**: Gate risky or external actions before execution.
- **Recording**: Log outcomes and evidence after each run.
- **Evolution**: Propose skill updates from feedback and failures.
""",
            source="probe-test",
        )
        return proposal.proposal_id


class WorkflowSpecRuntime:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.messages: list[str] = []

    def run(self, message: str) -> str:
        self.messages.append(message)
        store = WorkflowStore(self.state_dir / "workflows.sqlite3")
        spec = store.create_spec(
            WorkflowSpec(
                name="Community Trend Intelligence",
                goal="Watch community sources and report trend signals.",
                description="Generic recurring social trend workflow.",
                status=WorkflowStatus.PROPOSED,
                intent_type="scheduled_workflow",
                triggers=[{"type": "interval", "value": "interval:60s"}],
                sources=[{"kind": "community_web"}, {"kind": "reddit"}],
                steps=[
                    WorkflowStep(step_id="collect", step_type="collect", name="Collect sources"),
                    WorkflowStep(step_id="analyze", step_type="analyze", name="Analyze signals"),
                    WorkflowStep(step_id="report", step_type="report", name="Render report"),
                ],
                outputs=[{"kind": "report"}, {"kind": "notification", "channel": "ntfy"}],
                success_criteria=["A report is produced from recent collected resources."],
                policy={"approval": "required_for_external_submit"},
            )
        )
        return spec.workflow_id


class HarnessProbeTests(unittest.TestCase):
    def test_workflow_builder_probe_runs_interview_and_detects_new_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            runtime = ProposalRuntime(state_dir)

            result = run_workflow_builder_probe(
                load_app_config(),
                request="반복 자동화 워크플로우 만들어줘",
                answers=[
                    "커뮤니티 웹 페이지",
                    "1분마다 수집하고 1시간마다 보고",
                ],
                state_dir=state_dir,
                runtime=runtime,
            )

        self.assertTrue(result.ok)

    def test_workflow_spec_probe_creates_proposed_workflow_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            runtime = WorkflowSpecRuntime(state_dir)

            result = run_workflow_spec_probe(
                load_app_config(),
                request="주식 커뮤니티 트렌드를 계속 보고해줘",
                answers=["커뮤니티 웹과 레딧", "1분마다 수집하고 1시간마다 보고"],
                state_dir=state_dir,
                runtime=runtime,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.final_status, "proposed")
        self.assertEqual(len(result.new_workflows), 1)
        self.assertEqual(result.new_workflows[0]["status"], "proposed")
        self.assertIn("workflow_spec tool", runtime.messages[0])

    def test_workflow_builder_probe_preserves_extra_guidance_after_slots_are_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            runtime = ProposalRuntime(state_dir)

            result = run_workflow_builder_probe(
                load_app_config(),
                request="매일 WSJ 뉴스레터를 읽고 보고서로 알려줘",
                answers=["보유 주식 관점으로 평가해줘."],
                state_dir=state_dir,
                runtime=runtime,
            )

        self.assertTrue(result.ok)
        self.assertIn("Additional user guidance", runtime.messages[0])
        self.assertIn("보유 주식 관점", runtime.messages[0])

    def test_workflow_builder_probe_rejects_truncated_proposal_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            runtime = TruncatedProposalRuntime(state_dir)

            result = run_workflow_builder_probe(
                load_app_config(),
                request="반복 자동화 워크플로우 만들어줘",
                answers=["커뮤니티 웹 페이지", "1분마다"],
                state_dir=state_dir,
                runtime=runtime,
            )

        self.assertFalse(result.ok)
        self.assertIn("proposal quality failed", result.blocker)

    def test_workflow_builder_probe_accepts_bold_markdown_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            runtime = BoldLabelProposalRuntime(state_dir)

            result = run_workflow_builder_probe(
                load_app_config(),
                request="반복 자동화 워크플로우 만들어줘",
                answers=["커뮤니티 웹 페이지", "1분마다"],
                state_dir=state_dir,
                runtime=runtime,
            )

        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
