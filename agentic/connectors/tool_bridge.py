from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.approvals.service import ApprovalService
from agentic.connectors.registry import ConnectorRegistry
from agentic.policy import CapabilityRequest, PolicyAction, PolicyEngine
from agentic.traces.logger import TraceLogger


@dataclass(frozen=True)
class ConnectorExecutionResult:
    ok: bool
    result: Any = None
    approval_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None


class ConnectorToolBridge:
    def __init__(
        self,
        *,
        registry: ConnectorRegistry,
        policy: PolicyEngine,
        approvals: ApprovalService,
        trace: TraceLogger | None = None,
    ):
        self.registry = registry
        self.policy = policy
        self.approvals = approvals
        self.trace = trace

    def call_tool(
        self,
        connector_id: str,
        name: str,
        arguments: dict[str, Any],
    ) -> ConnectorExecutionResult:
        capability = f"connector:{connector_id}:tool:{name}"
        decision = self.policy.decide(
            CapabilityRequest(
                capability=capability,
                action="execute",
                resource=f"{connector_id}.{name}",
                payload={"arguments": arguments},
            )
        )
        if decision.action == PolicyAction.DENY:
            return ConnectorExecutionResult(
                ok=False,
                error_type="policy_denied",
                error_message=decision.reason,
            )
        if decision.action == PolicyAction.REQUIRE_APPROVAL:
            request = self.approvals.create_request(
                capability=capability,
                reason=decision.reason,
                payload={"connector_id": connector_id, "tool": name, "arguments": arguments},
            )
            return ConnectorExecutionResult(
                ok=False,
                approval_id=request.approval_id,
                error_type="approval_required",
                error_message=decision.reason,
            )
        try:
            result = self.registry.call_tool(connector_id, name, arguments)
        except Exception as exc:
            return ConnectorExecutionResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        if self.trace is not None:
            self.trace.record(
                "connector_tool_called",
                {"connector_id": connector_id, "tool": name, "ok": True},
            )
        return ConnectorExecutionResult(ok=True, result=result)
