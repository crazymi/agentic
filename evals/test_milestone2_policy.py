from __future__ import annotations

import unittest

from agentic.policy import CapabilityRequest, PolicyAction, PolicyEngine


class Milestone2PolicyTests(unittest.TestCase):
    def test_add_tool_is_allowed(self) -> None:
        decision = PolicyEngine().decide(
            CapabilityRequest(capability="tool:add", action="execute")
        )

        self.assertEqual(decision.action, PolicyAction.ALLOW)

    def test_sensitive_tool_requires_approval(self) -> None:
        decision = PolicyEngine().decide(
            CapabilityRequest(capability="tool:shell", action="execute")
        )

        self.assertEqual(decision.action, PolicyAction.REQUIRE_APPROVAL)

    def test_denied_tool_is_denied(self) -> None:
        decision = PolicyEngine().decide(
            CapabilityRequest(capability="tool:credential_exfiltration", action="execute")
        )

        self.assertEqual(decision.action, PolicyAction.DENY)

    def test_unknown_tool_requires_approval(self) -> None:
        decision = PolicyEngine().decide(
            CapabilityRequest(capability="tool:new_external_action", action="execute")
        )

        self.assertEqual(decision.action, PolicyAction.REQUIRE_APPROVAL)


if __name__ == "__main__":
    unittest.main()
