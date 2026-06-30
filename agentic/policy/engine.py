from __future__ import annotations

from agentic.policy.rules import CapabilityRequest, PolicyAction, PolicyDecision


APPROVAL_REQUIRED_CAPABILITIES = {
    "tool:shell",
    "tool:file_write",
    "tool:browser_submit",
    "tool:payment",
    "tool:email_send",
}

DENIED_CAPABILITIES = {
    "tool:destructive_git",
    "tool:credential_exfiltration",
}


class PolicyEngine:
    def decide(self, request: CapabilityRequest) -> PolicyDecision:
        if request.capability == "tool:add":
            return PolicyDecision(PolicyAction.ALLOW, "safe local arithmetic tool")
        if request.capability in DENIED_CAPABILITIES:
            return PolicyDecision(PolicyAction.DENY, "capability is denied")
        if request.capability in APPROVAL_REQUIRED_CAPABILITIES:
            return PolicyDecision(
                PolicyAction.REQUIRE_APPROVAL,
                "capability requires user approval",
            )
        if request.capability.startswith("tool:"):
            return PolicyDecision(
                PolicyAction.REQUIRE_APPROVAL,
                "unknown tool capability requires approval",
            )
        return PolicyDecision(
            PolicyAction.REQUIRE_APPROVAL,
            "unknown capability requires approval",
        )
