from __future__ import annotations

from agentic.tooling.models import ToolingKind, ToolingPlan, ToolingRequest
from agentic.workflow_kernel.capabilities import (
    CapabilityAdmission,
    CapabilityNeed,
    CapabilityPlan,
)


class ToolingPlanner:
    """Turns capability gaps into concrete harness/tooling build requests."""

    def plan(self, capability_plan: CapabilityPlan) -> ToolingPlan:
        requests = [
            request
            for need in capability_plan.needs
            if (request := self._request_for_need(capability_plan.workflow_id, need)) is not None
        ]
        return ToolingPlan(workflow_id=capability_plan.workflow_id, requests=requests)

    def _request_for_need(self, workflow_id: str, need: CapabilityNeed) -> ToolingRequest | None:
        if need.admission == CapabilityAdmission.ALLOWED:
            return None
        if need.admission == CapabilityAdmission.MISSING:
            return ToolingRequest(
                workflow_id=workflow_id,
                capability=need.capability,
                action=need.action,
                resource=need.resource,
                kind=self._kind_for_capability(need.capability),
                reason=need.reason,
                suggested_module=self._module_for_capability(need.capability),
                priority=0 if need.capability.startswith("connector:browser") else 1,
                payload=need.payload,
            )
        if need.admission == CapabilityAdmission.NEEDS_ARTIFACT_REVIEW:
            return ToolingRequest(
                workflow_id=workflow_id,
                capability=need.capability,
                action=need.action,
                resource=need.resource,
                kind=ToolingKind.ARTIFACT_REVIEW,
                reason=need.reason,
                suggested_module="agentic/artifacts/admission.py",
                priority=1,
                payload=need.payload,
            )
        if need.admission == CapabilityAdmission.REQUIRES_APPROVAL:
            return ToolingRequest(
                workflow_id=workflow_id,
                capability=need.capability,
                action=need.action,
                resource=need.resource,
                kind=ToolingKind.POLICY,
                reason=need.reason,
                suggested_module="agentic/approvals/",
                priority=2,
                payload=need.payload,
            )
        if need.admission == CapabilityAdmission.DENIED:
            return ToolingRequest(
                workflow_id=workflow_id,
                capability=need.capability,
                action=need.action,
                resource=need.resource,
                kind=ToolingKind.POLICY,
                reason=need.reason,
                suggested_module="agentic/policy/",
                priority=0,
                payload=need.payload,
            )
        return None

    @staticmethod
    def _kind_for_capability(capability: str) -> ToolingKind:
        if capability.startswith("connector:"):
            return ToolingKind.CONNECTOR
        if capability.startswith("tool:"):
            return ToolingKind.TOOL
        if capability.startswith("runtime:"):
            return ToolingKind.RUNTIME
        if capability.startswith("skill:"):
            return ToolingKind.SKILL
        return ToolingKind.RUNTIME

    @staticmethod
    def _module_for_capability(capability: str) -> str:
        if capability == "connector:browser":
            return "agentic/browser/"
        if capability.startswith("connector:"):
            return "agentic/connectors/"
        if capability.startswith("tool:"):
            return "agentic/tools/"
        if capability.startswith("runtime:"):
            return "agentic/runtime/"
        if capability.startswith("skill:"):
            return "skills/"
        return "agentic/"

