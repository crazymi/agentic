from __future__ import annotations

from agentic.policy.rules import CapabilityRequest, PolicyAction, PolicyDecision


APPROVAL_REQUIRED_CAPABILITIES = {
    "artifact:script",
    "channel:ntfy",
    "connector:browser_page",
    "connector:community_web",
    "connector:reddit",
    "connector:web_page",
    "tool:booking",
    "tool:browser_submit",
    "tool:email_send",
    "tool:edit_file",
    "tool:exec",
    "tool:shell",
    "tool:file_write",
    "tool:payment",
    "tool:process",
    "tool:python_execute",
    "tool:write_file",
    "tool:apply_patch",
}

DENIED_CAPABILITIES = {
    "tool:destructive_git",
    "tool:credential_exfiltration",
}


class PolicyEngine:
    def decide(self, request: CapabilityRequest) -> PolicyDecision:
        if request.capability == "tool:add":
            return PolicyDecision(PolicyAction.ALLOW, "safe local arithmetic tool")
        if request.capability in {
            "tool:read_file",
            "tool:list_files",
            "tool:search_files",
            "tool:web_search",
        }:
            return PolicyDecision(PolicyAction.ALLOW, "read-only local or web lookup tool")
        if request.capability in DENIED_CAPABILITIES:
            return PolicyDecision(PolicyAction.DENY, "capability is denied")
        if request.capability in APPROVAL_REQUIRED_CAPABILITIES:
            return PolicyDecision(
                PolicyAction.REQUIRE_APPROVAL,
                "capability requires user approval",
            )
        if request.capability.startswith("connector:"):
            return PolicyDecision(
                PolicyAction.REQUIRE_APPROVAL,
                "connector capability requires approval",
            )
        if request.capability.startswith("artifact:"):
            return PolicyDecision(
                PolicyAction.REQUIRE_APPROVAL,
                "artifact capability requires approval",
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
