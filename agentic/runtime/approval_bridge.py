from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.approvals.service import ApprovalService
from agentic.channels.ntfy import NtfyChannel
from agentic.policy.engine import PolicyEngine
from agentic.policy.rules import CapabilityRequest, PolicyAction
from agentic.runtime.tool_bridge import ToolBridge, ToolExecutionResult
from agentic.tools.parser import parse_tool_call
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class ApprovalToolResult:
    ok: bool
    tool_result: ToolExecutionResult | None = None
    approval_id: str | None = None
    status: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    result: Any = None


class ApprovalToolBridge:
    def __init__(
        self,
        *,
        tool_bridge: ToolBridge,
        policy: PolicyEngine,
        approvals: ApprovalService,
        trace: TraceLogger | None = None,
        ntfy: NtfyChannel | None = None,
    ):
        self.tool_bridge = tool_bridge
        self.policy = policy
        self.approvals = approvals
        self.trace = trace
        self.ntfy = ntfy

    def execute_tool_call_text(self, text: str) -> ApprovalToolResult:
        try:
            call = parse_tool_call(text)
        except ValueError as exc:
            return ApprovalToolResult(
                ok=False,
                error_type="malformed_tool_call",
                error_message=str(exc),
            )

        capability = f"tool:{call.tool}"
        decision = self.policy.decide(
            CapabilityRequest(
                capability=capability,
                action="execute",
                resource=call.tool,
                payload={"arguments": call.arguments},
            )
        )

        if decision.action == PolicyAction.ALLOW:
            self._record("tool_allowed_by_policy", capability, decision.reason)
            result = self.tool_bridge.execute_tool_call_text(text)
            return ApprovalToolResult(
                ok=result.ok,
                tool_result=result,
                status="allowed",
                error_type=result.error_type,
                error_message=result.error_message,
                result=result.result,
            )

        if decision.action == PolicyAction.DENY:
            self._record("tool_denied_by_policy", capability, decision.reason)
            return ApprovalToolResult(
                ok=False,
                status="denied",
                error_type="policy_denied",
                error_message=decision.reason,
            )

        request = self.approvals.create_request(
            capability=capability,
            reason=decision.reason,
            payload={
                "tool": call.tool,
                "arguments": call.arguments,
                "tool_call_text": text,
            },
            )
        self._record("approval_required", capability, decision.reason)
        if self.ntfy is not None:
            sent = self.ntfy.send_approval_request(request)
            if self.trace is not None:
                self.trace.record(
                    "approval_notification_sent",
                    {"approval_id": request.approval_id, "sent": sent},
                )
        if self.trace is not None:
            self.trace.record(
                "tool_blocked_by_approval",
                {
                    "approval_id": request.approval_id,
                    "capability": capability,
                    "tool": call.tool,
                },
            )
        return ApprovalToolResult(
            ok=False,
            approval_id=request.approval_id,
            status="approval_required",
            error_type="approval_required",
            error_message=decision.reason,
        )

    def execute_approved(self, approval_id: str) -> ApprovalToolResult:
        request = self.approvals.get(approval_id)
        if request.status.value != "approved":
            return ApprovalToolResult(
                ok=False,
                approval_id=approval_id,
                status=request.status.value,
                error_type="approval_not_approved",
                error_message=f"approval {approval_id} is {request.status.value}",
            )
        text = str(request.payload.get("tool_call_text", ""))
        result = self.tool_bridge.execute_tool_call_text(text)
        return ApprovalToolResult(
            ok=result.ok,
            approval_id=approval_id,
            status="approved_executed",
            tool_result=result,
            result=result.result,
            error_type=result.error_type,
            error_message=result.error_message,
        )

    def _record(self, event_type: str, capability: str, reason: str) -> None:
        if self.trace is None:
            return
        self.trace.record(
            event_type,
            {
                "capability": capability,
                "reason": reason,
            },
        )
