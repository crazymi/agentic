from __future__ import annotations

from typing import Any

from agentic.approvals.models import ApprovalRequest, ApprovalStatus
from agentic.approvals.store import ApprovalStore
from agentic.traces.logger import TraceLogger


class ApprovalService:
    def __init__(self, store: ApprovalStore, trace: TraceLogger | None = None):
        self.store = store
        self.trace = trace

    def create_request(
        self,
        *,
        capability: str,
        reason: str,
        payload: dict[str, Any],
    ) -> ApprovalRequest:
        request = self.store.append(
            ApprovalRequest(
                capability=capability,
                reason=reason,
                payload=payload,
            )
        )
        self._record("approval_requested", request)
        return request

    def approve(self, approval_id: str) -> ApprovalRequest:
        request = self.store.get(approval_id).transition(ApprovalStatus.APPROVED)
        self.store.update(request)
        self._record("approval_decided", request)
        return request

    def deny(self, approval_id: str) -> ApprovalRequest:
        request = self.store.get(approval_id).transition(ApprovalStatus.DENIED)
        self.store.update(request)
        self._record("approval_decided", request)
        return request

    def expire(self, approval_id: str) -> ApprovalRequest:
        request = self.store.get(approval_id).transition(ApprovalStatus.EXPIRED)
        self.store.update(request)
        self._record("approval_decided", request)
        return request

    def get_pending(self) -> list[ApprovalRequest]:
        return self.store.pending()

    def get(self, approval_id: str) -> ApprovalRequest:
        return self.store.get(approval_id)

    def _record(self, event_type: str, request: ApprovalRequest) -> None:
        if self.trace is None:
            return
        self.trace.record(
            event_type,
            {
                "approval_id": request.approval_id,
                "capability": request.capability,
                "reason": request.reason,
                "status": request.status.value,
            },
        )
