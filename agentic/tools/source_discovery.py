from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic.sources.discovery import build_source_candidate_service
from agentic.tools.base import ToolSpec


def source_candidate_tool(state_dir: str | Path | None = None) -> ToolSpec:
    root = Path(state_dir) if state_dir is not None else Path("traces/state")

    def _source_candidate(
        *,
        action: str,
        requested_source: str,
        kind: str,
        name: str,
        locator: str,
        workflow_id: str = "",
        aliases: list[str] | None = None,
        confidence: float = 0.0,
        rationale: str = "",
        evidence: list[dict[str, Any]] | None = None,
        auto_register: bool = False,
    ) -> dict[str, Any]:
        if action != "create":
            raise ValueError(f"unsupported source_candidate action: {action}")
        return build_source_candidate_service(root).propose(
            workflow_id=workflow_id,
            requested_source=requested_source,
            kind=kind,
            name=name,
            locator=locator,
            aliases=aliases or [],
            confidence=confidence,
            rationale=rationale,
            evidence=evidence or [],
            auto_register=auto_register,
        )

    return ToolSpec(
        name="source_candidate",
        description=(
            "Store a candidate external source discovered by the agent. "
            "Can auto-register a high-confidence public read-only web_page source."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create"]},
                "workflow_id": {"type": "string"},
                "requested_source": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["web_page", "feed", "mail", "browser_page", "local_file", "repo_state"],
                },
                "name": {"type": "string"},
                "locator": {"type": "string"},
                "aliases": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
                "auto_register": {"type": "boolean"},
            },
            "required": ["action", "requested_source", "kind", "name", "locator"],
        },
        fn=_source_candidate,
    )
