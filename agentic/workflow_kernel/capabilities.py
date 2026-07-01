from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentic.policy.engine import PolicyEngine
from agentic.policy.rules import CapabilityRequest, PolicyAction
from agentic.workflow_kernel.models import StepType, WorkflowSpec


class CapabilityAdmission(StrEnum):
    ALLOWED = "allowed"
    REQUIRES_APPROVAL = "requires_approval"
    DENIED = "denied"
    MISSING = "missing"
    NEEDS_ARTIFACT_REVIEW = "needs_artifact_review"


@dataclass(frozen=True)
class CapabilityNeed:
    capability: str
    action: str
    resource: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    admission: CapabilityAdmission = CapabilityAdmission.MISSING
    reason: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "action": self.action,
            "resource": self.resource,
            "payload": self.payload,
            "admission": self.admission.value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CapabilityPlan:
    workflow_id: str
    needs: list[CapabilityNeed]

    @property
    def blocked(self) -> bool:
        return any(need.admission in {CapabilityAdmission.DENIED, CapabilityAdmission.MISSING} for need in self.needs)

    @property
    def requires_approval(self) -> bool:
        return any(
            need.admission
            in {CapabilityAdmission.REQUIRES_APPROVAL, CapabilityAdmission.NEEDS_ARTIFACT_REVIEW}
            for need in self.needs
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "blocked": self.blocked,
            "requires_approval": self.requires_approval,
            "needs": [need.to_record() for need in self.needs],
        }


class CapabilityPlanner:
    def __init__(
        self,
        *,
        policy: PolicyEngine | None = None,
        allowlisted_connectors: set[str] | None = None,
    ):
        self.policy = policy or PolicyEngine()
        self.allowlisted_connectors = allowlisted_connectors or {
            "fake",
            "fixture",
            "mail",
            "channel",
            "repo",
        }

    def plan(self, spec: WorkflowSpec) -> CapabilityPlan:
        needs: list[CapabilityNeed] = []
        for step in spec.steps:
            needs.extend(self._needs_for_step(spec.workflow_id, step.step_type, step.config))
        return CapabilityPlan(workflow_id=spec.workflow_id, needs=needs)

    def _needs_for_step(
        self,
        workflow_id: str,
        step_type: StepType,
        config: dict[str, Any],
    ) -> list[CapabilityNeed]:
        if step_type == StepType.COLLECT:
            source = str(config.get("source") or "unknown")
            return [self._connector_need(source, action="read")]
        if step_type == StepType.CALL_CONNECTOR:
            connector = str(config.get("connector") or config.get("source") or "unknown")
            return [self._connector_need(connector, action=str(config.get("action") or "read"))]
        if step_type == StepType.CALL_TOOL:
            tool = str(config.get("tool") or "unknown")
            return [self._policy_need(f"tool:{tool}", str(config.get("action") or "execute"), "", config)]
        if step_type == StepType.RUN_SCRIPT:
            return [
                CapabilityNeed(
                    capability="artifact:script",
                    action="execute",
                    resource=str(config.get("artifact_id") or "generated_script"),
                    payload={"workflow_id": workflow_id},
                    admission=CapabilityAdmission.NEEDS_ARTIFACT_REVIEW,
                    reason="generated scripts require artifact admission and approval",
                )
            ]
        if step_type == StepType.NOTIFY:
            channel = str(config.get("channel") or "web")
            if channel == "ntfy":
                return [self._policy_need("channel:ntfy", "send", "user_notification", config)]
        if step_type == StepType.APPROVAL:
            return [
                CapabilityNeed(
                    capability="approval",
                    action="wait",
                    admission=CapabilityAdmission.REQUIRES_APPROVAL,
                    reason="workflow step explicitly waits for approval",
                )
            ]
        return [
            CapabilityNeed(
                capability=f"workflow_step:{step_type.value}",
                action="execute",
                admission=CapabilityAdmission.ALLOWED,
                reason="deterministic workflow step",
            )
        ]

    def _connector_need(self, connector: str, *, action: str) -> CapabilityNeed:
        if connector in {"reddit", "community_web", "web_page"}:
            return CapabilityNeed(
                capability=f"connector:{connector}",
                action=action,
                resource=connector,
                admission=CapabilityAdmission.REQUIRES_APPROVAL,
                reason="external source connector is not enabled by default",
            )
        if connector not in self.allowlisted_connectors:
            return CapabilityNeed(
                capability=f"connector:{connector}",
                action=action,
                resource=connector,
                admission=CapabilityAdmission.MISSING,
                reason="connector is not allowlisted or implemented",
            )
        return CapabilityNeed(
            capability=f"connector:{connector}",
            action=action,
            resource=connector,
            admission=CapabilityAdmission.ALLOWED,
            reason="connector is allowlisted for read-only workflow use",
        )

    def _policy_need(
        self,
        capability: str,
        action: str,
        resource: str,
        payload: dict[str, Any],
    ) -> CapabilityNeed:
        decision = self.policy.decide(
            CapabilityRequest(
                capability=capability,
                action=action,
                resource=resource,
                payload=payload,
            )
        )
        if decision.action == PolicyAction.ALLOW:
            admission = CapabilityAdmission.ALLOWED
        elif decision.action == PolicyAction.REQUIRE_APPROVAL:
            admission = CapabilityAdmission.REQUIRES_APPROVAL
        else:
            admission = CapabilityAdmission.DENIED
        return CapabilityNeed(
            capability=capability,
            action=action,
            resource=resource,
            payload=payload,
            admission=admission,
            reason=decision.reason,
        )
