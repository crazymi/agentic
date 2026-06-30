from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.approvals.models import ApprovalStatus
from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.traces.logger import TraceLogger


class Milestone2ApprovalTests(unittest.TestCase):
    def test_create_approve_and_rebuild_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "approvals.jsonl"
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            service = ApprovalService(ApprovalStore(path), trace=trace)

            first = service.create_request(
                capability="tool:shell",
                reason="needs approval",
                payload={"command": "echo hi"},
            )
            second = service.create_request(
                capability="tool:file_write",
                reason="needs approval",
                payload={"path": "x"},
            )
            approved = service.approve(first.approval_id)

            rebuilt = ApprovalService(ApprovalStore(path))
            pending_ids = [item.approval_id for item in rebuilt.get_pending()]

        self.assertEqual(approved.status, ApprovalStatus.APPROVED)
        self.assertEqual(pending_ids, [second.approval_id])

    def test_invalid_transition_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ApprovalService(ApprovalStore(Path(tmpdir) / "approvals.jsonl"))
            request = service.create_request(
                capability="tool:shell",
                reason="needs approval",
                payload={},
            )
            service.deny(request.approval_id)

            with self.assertRaises(ValueError):
                service.approve(request.approval_id)

    def test_decisions_are_traced(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            service = ApprovalService(
                ApprovalStore(Path(tmpdir) / "approvals.jsonl"),
                trace=trace,
            )
            request = service.create_request(
                capability="tool:shell",
                reason="needs approval",
                payload={},
            )
            service.deny(request.approval_id)

            event_types = [event.event_type for event in trace.read_events()]

        self.assertEqual(event_types, ["approval_requested", "approval_decided"])


if __name__ == "__main__":
    unittest.main()
