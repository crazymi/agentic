from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def credential_id() -> str:
    return f"cred_{uuid4().hex}"


class CredentialKind(StrEnum):
    ENV_VAR = "env_var"
    LOCAL_KEY_ID = "local_key_id"
    OAUTH_PROFILE = "oauth_profile"
    MANUAL_REFERENCE = "manual_reference"


@dataclass(frozen=True)
class CredentialRef:
    provider: str
    purpose: str
    reference: str
    kind: CredentialKind = CredentialKind.ENV_VAR
    credential_id: str = field(default_factory=credential_id)
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", CredentialKind(self.kind))
        if not self.provider:
            raise ValueError("credential provider must not be empty")
        if not self.purpose:
            raise ValueError("credential purpose must not be empty")
        if not self.reference:
            raise ValueError("credential reference must not be empty")
        _reject_secret_like_values(self.reference, self.metadata)

    def safe_label(self) -> str:
        return f"{self.provider}:{self.kind.value}:{self.reference}"

    def to_record(self) -> dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "provider": self.provider,
            "purpose": self.purpose,
            "reference": self.reference,
            "kind": self.kind.value,
            "scopes": self.scopes,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "CredentialRef":
        return cls(
            credential_id=str(record["credential_id"]),
            provider=str(record["provider"]),
            purpose=str(record["purpose"]),
            reference=str(record["reference"]),
            kind=CredentialKind(record.get("kind", CredentialKind.ENV_VAR.value)),
            scopes=list(record.get("scopes") or []),
            metadata=dict(record.get("metadata") or {}),
            created_at=str(record.get("created_at") or utc_now()),
        )


def _reject_secret_like_values(reference: str, metadata: dict[str, Any]) -> None:
    forbidden_keys = {"secret", "token", "password", "api_key", "apikey", "value"}
    if len(reference) > 120:
        raise ValueError("credential reference looks too long; store only a reference, not the secret")
    if any(marker in reference.lower() for marker in ("-----begin", "sk-", "ghp_", "xoxb-")):
        raise ValueError("credential reference appears to contain a raw secret")
    for key in metadata:
        lowered = str(key).lower()
        if lowered in forbidden_keys or any(marker in lowered for marker in forbidden_keys):
            raise ValueError(f"credential metadata must not contain secret-like key: {key}")
