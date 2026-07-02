from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.skills import SkillProposalStatus, SkillWorkshopService, SkillWorkshopStore
from agentic.skills.loader import SkillLoader
from agentic.tools.skill_workshop import skill_workshop_tool


PROPOSAL_BODY = """---
name: workflow-building
description: Guide the agent through vague workflow requests.
---

# Workflow Building

Ask one missing question at a time, discover required capabilities, and create proposals instead of active files.
"""


class SkillWorkshopTests(unittest.TestCase):
    def test_create_persists_pending_proposal_without_active_skill_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )

            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body=PROPOSAL_BODY,
            )
            reloaded = service.inspect(proposal.proposal_id)

            self.assertEqual(reloaded.status, SkillProposalStatus.PENDING)
            self.assertEqual(reloaded.name, "workflow-building")
            self.assertFalse((root / "skills" / "workflow-building" / "SKILL.md").exists())

    def test_existing_active_skill_blocks_create_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )

            with self.assertRaises(ValueError):
                service.propose_create(
                    name="workflow-building",
                    description="Guide vague workflow requests",
                    proposal_body=PROPOSAL_BODY,
                )

    def test_existing_active_skill_can_receive_revision_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )

            proposal = service.propose_revision(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Updated workflow building",
            )

        self.assertEqual(proposal.metadata["proposal_kind"], "revision")

    def test_review_create_proposal_shows_candidate_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Workflow Building",
            )

            review = service.review(proposal.proposal_id)

        self.assertEqual(review.mode, "create")
        self.assertFalse(review.active_exists)
        self.assertTrue(review.validation_ok)
        self.assertTrue(review.candidate_hash)
        self.assertTrue(review.review_hash)
        self.assertIn("+++ proposal:", review.diff)
        self.assertIn("# Workflow Building", review.candidate_text)

    def test_review_revision_proposal_shows_active_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            proposal = service.propose_revision(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Updated workflow building",
            )

            review = service.review(proposal.proposal_id)

        self.assertEqual(review.mode, "revision")
        self.assertTrue(review.active_exists)
        self.assertTrue(review.validation_ok)
        self.assertTrue(review.active_hash)
        self.assertTrue(review.diff_hash)
        self.assertIn("---", review.diff)
        self.assertIn("Updated workflow building", review.diff)

    def test_review_normalizes_indented_markdown_list_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Workflow Building\n        - Ask one question.",
            )

            review = service.review(proposal.proposal_id)

        self.assertIn("\n- Ask one question.", review.candidate_text)
        self.assertNotIn("\n        - Ask one question.", review.candidate_text)

    def test_reject_and_quarantine_are_terminal_for_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = SkillWorkshopService(
                SkillWorkshopStore(Path(tmpdir) / "skill_workshop.sqlite3"),
                skills_root=Path(tmpdir) / "skills",
            )
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body=PROPOSAL_BODY,
            )

            rejected = service.reject(proposal.proposal_id, reason="needs better evidence")

            self.assertEqual(rejected.status, SkillProposalStatus.REJECTED)
            with self.assertRaises(ValueError):
                service.revise(rejected.proposal_id, proposal_body=PROPOSAL_BODY)

    def test_skill_workshop_tool_creates_and_lists_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = skill_workshop_tool(
                Path(tmpdir) / "skill_workshop.sqlite3",
                skills_root=Path(tmpdir) / "skills",
            )

            created = tool.fn(
                action="create",
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body=PROPOSAL_BODY,
            )
            listed = tool.fn(action="list")

        self.assertTrue(created["ok"])
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["proposals"][0]["name"], "workflow-building")

    def test_skill_workshop_tool_converts_duplicate_create_to_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            tool = skill_workshop_tool(
                root / "skill_workshop.sqlite3",
                skills_root=root / "skills",
            )

            created = tool.fn(
                action="create",
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Updated workflow building",
            )

        self.assertTrue(created["ok"])
        self.assertEqual(created["proposal"]["metadata"]["proposal_kind"], "revision")

    def test_apply_revision_overwrites_existing_active_skill_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            proposal = service.propose_revision(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Updated workflow building",
            )
            approval = approvals.approve(
                service.request_apply(proposal.proposal_id, approvals=approvals).approval_id
            )

            applied = service.apply(proposal.proposal_id, approval=approval)
            loaded = SkillLoader(root / "skills").load(active)

        self.assertEqual(applied.status, SkillProposalStatus.APPLIED)
        self.assertIn("Updated workflow building", loaded.body)

    def test_default_registry_exposes_skill_workshop_tool(self) -> None:
        from agentic.tools.registry import ToolRegistry

        names = {schema["name"] for schema in ToolRegistry.with_defaults().schemas()}

        self.assertIn("skill_workshop", names)

    def test_apply_requires_approved_matching_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Workflow Building\n\nAsk one question at a time.",
            )
            pending = service.request_apply(proposal.proposal_id, approvals=approvals)

            self.assertIn("candidate_hash", pending.payload)
            self.assertIn("review_hash", pending.payload)
            with self.assertRaisesRegex(ValueError, "approval must be approved"):
                service.apply(proposal.proposal_id, approval=pending)

            approved = approvals.approve(pending.approval_id)
            applied = service.apply(proposal.proposal_id, approval=approved)
            loaded = SkillLoader(root / "skills").load(
                root / "skills" / "workflow-building" / "SKILL.md"
            )

        self.assertEqual(applied.status, SkillProposalStatus.APPLIED)
        self.assertEqual(loaded.manifest.name, "workflow-building")
        self.assertIn("Ask one question", loaded.body)

    def test_apply_rejects_when_active_skill_changed_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / "skills" / "workflow-building" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text(PROPOSAL_BODY, encoding="utf-8")
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            proposal = service.propose_revision(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Updated workflow building",
            )
            approval = approvals.approve(
                service.request_apply(proposal.proposal_id, approvals=approvals).approval_id
            )
            active.write_text(PROPOSAL_BODY + "\nChanged after review.\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "active_hash"):
                service.apply(proposal.proposal_id, approval=approval)

    def test_apply_rejects_stale_approval_after_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# v1",
            )
            approval = approvals.approve(
                service.request_apply(proposal.proposal_id, approvals=approvals).approval_id
            )
            service.revise(proposal.proposal_id, proposal_body="# v2")

            with self.assertRaisesRegex(ValueError, "content_hash"):
                service.apply(proposal.proposal_id, approval=approval)

    def test_apply_rejects_wrong_approval_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            service = SkillWorkshopService(
                SkillWorkshopStore(root / "skill_workshop.sqlite3"),
                skills_root=root / "skills",
            )
            approvals = ApprovalService(ApprovalStore(root / "approvals.jsonl"))
            proposal = service.propose_create(
                name="workflow-building",
                description="Guide vague workflow requests",
                proposal_body="# Workflow Building",
            )
            wrong = approvals.approve(
                approvals.create_request(
                    capability="skill:apply",
                    reason="wrong",
                    payload={
                        "proposal_id": "other",
                        "target_skill_name": proposal.target_skill_name,
                        "content_hash": proposal.content_hash,
                    },
                ).approval_id
            )

            with self.assertRaisesRegex(ValueError, "proposal_id"):
                service.apply(proposal.proposal_id, approval=wrong)


if __name__ == "__main__":
    unittest.main()
