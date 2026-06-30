from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agentic.runtime.events import ensure_json_payload


class PolicyAction(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True)
class CapabilityRequest:
    capability: str
    action: str
    resource: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capability:
            raise ValueError("capability must not be empty")
        if not self.action:
            raise ValueError("action must not be empty")
        object.__setattr__(self, "payload", ensure_json_payload(self.payload))


@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyAction
    reason: str

    @property
    def allowed(self) -> bool:
        return self.action == PolicyAction.ALLOW

    @property
    def requires_approval(self) -> bool:
        return self.action == PolicyAction.REQUIRE_APPROVAL

    @property
    def denied(self) -> bool:
        return self.action == PolicyAction.DENY
