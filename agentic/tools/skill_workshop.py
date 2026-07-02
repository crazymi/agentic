from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic.tools.base import ToolSpec


DEFAULT_SKILL_WORKSHOP_DB = Path("traces/state/skill_workshop.sqlite3")


def skill_workshop_tool(
    store_path: str | Path = DEFAULT_SKILL_WORKSHOP_DB,
    *,
    skills_root: str | Path = "skills",
) -> ToolSpec:
    from agentic.skills.workshop import SkillWorkshopService, SkillWorkshopStore

    service = SkillWorkshopService(
        SkillWorkshopStore(store_path),
        skills_root=skills_root,
    )

    def _skill_workshop(
        action: str,
        name: str = "",
        description: str = "",
        proposal_body: str = "",
        proposal_id: str = "",
        reason: str = "",
        source: str = "agent",
        status: str = "",
        limit: int = 20,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if action == "create":
            try:
                proposal = service.propose_create(
                    name=name,
                    description=description,
                    proposal_body=proposal_body,
                    source=source,
                    metadata=metadata or {},
                )
            except ValueError as exc:
                if "target skill already exists" not in str(exc):
                    raise
                proposal = service.propose_revision(
                    name=name,
                    description=description,
                    proposal_body=proposal_body,
                    source=source,
                    metadata={
                        **(metadata or {}),
                        "recovered_from_error": str(exc),
                    },
                )
            return {"ok": True, "proposal": proposal.to_record()}
        if action == "inspect":
            proposal = service.inspect(proposal_id)
            return {"ok": True, "proposal": proposal.to_record()}
        if action == "list":
            proposals = service.list(status=status or None, limit=limit)
            return {"ok": True, "proposals": [proposal.to_record() for proposal in proposals]}
        if action == "revise":
            proposal = service.revise(proposal_id, proposal_body=proposal_body, reason=reason)
            return {"ok": True, "proposal": proposal.to_record()}
        if action == "reject":
            proposal = service.reject(proposal_id, reason=reason)
            return {"ok": True, "proposal": proposal.to_record()}
        if action == "quarantine":
            proposal = service.quarantine(proposal_id, reason=reason)
            return {"ok": True, "proposal": proposal.to_record()}
        raise ValueError(f"unsupported skill_workshop action: {action}")

    return ToolSpec(
        name="skill_workshop",
        description=(
            "Create and manage pending skill proposals. This tool never writes active SKILL.md files; "
            "it records proposal records for human review."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "inspect", "list", "revise", "reject", "quarantine"],
                },
                "name": {"type": "string"},
                "description": {"type": "string"},
                "proposal_body": {"type": "string"},
                "proposal_id": {"type": "string"},
                "reason": {"type": "string"},
                "source": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
                "metadata": {"type": "object"},
            },
            "required": ["action"],
        },
        fn=_skill_workshop,
    )
