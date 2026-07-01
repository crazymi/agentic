from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic.sources import SourceDefinition, SourceKind, SourceStore
from agentic.workflow_kernel.models import StepType, WorkflowSpec


def bind_checked_in_local_source(
    spec: WorkflowSpec,
    *,
    source_store: SourceStore,
    repo_root: str | Path | None = None,
) -> WorkflowSpec:
    source_type = str(spec.inputs.get("source") or _first_source_type(spec) or "")
    binding = _binding_for_source(source_type, repo_root=Path(repo_root) if repo_root else _repo_root())
    if binding is None:
        return spec
    source = source_store.add_source(
        SourceDefinition(
            kind=binding["kind"],
            name=binding["name"],
            locator=binding["locator"],
            enabled=True,
            metadata={"binding": "checked_in_local_source", "requested_source": source_type},
        )
    )
    record = spec.to_record()
    record["inputs"] = {
        **dict(record.get("inputs") or {}),
        "source_id": source.source_id,
        "source": source.kind.value,
        "requested_source": source_type,
    }
    record["sources"] = [
        {
            "source_id": source.source_id,
            "kind": source.kind.value,
            "locator": source.locator,
            "mode": "checked_in_local_source",
            "requested_source": source_type,
        }
    ]
    record["capabilities"] = [
        {"capability": f"source:{source.kind.value}:read", "risk": "low"}
    ]
    record["assumptions"] = [
        *list(record.get("assumptions") or []),
        f"Bound requested source '{source_type}' to checked-in local source '{source.name}'.",
    ]
    record["steps"] = [
        _bind_collect_step(step, source.source_id, source.kind.value)
        for step in list(record.get("steps") or [])
    ]
    return WorkflowSpec.from_record(record)


def _bind_collect_step(step: dict[str, Any], source_id: str, source_kind: str) -> dict[str, Any]:
    if step.get("step_type") != StepType.COLLECT.value:
        return step
    return {
        **step,
        "config": {
            **dict(step.get("config") or {}),
            "source": source_kind,
            "source_id": source_id,
        },
    }


def _first_source_type(spec: WorkflowSpec) -> str:
    for source in spec.sources:
        if "type" in source:
            return str(source["type"])
        if "kind" in source:
            return str(source["kind"])
    return ""


def _binding_for_source(source_type: str, *, repo_root: Path) -> dict[str, Any] | None:
    examples = repo_root / "examples" / "sources"
    if source_type in {"mail", "gmail"}:
        return {
            "kind": SourceKind.MAIL,
            "name": "Checked-in WSJ newsletter source",
            "locator": (examples / "wsj_newsletter.jsonl").as_uri(),
        }
    if source_type in {"community_web", "reddit", "feed"}:
        return {
            "kind": SourceKind.FEED,
            "name": "Checked-in market community source",
            "locator": (examples / "market_community_posts.jsonl").as_uri(),
        }
    if source_type in {"channel", "ideas", "local_file"}:
        return {
            "kind": SourceKind.LOCAL_FILE,
            "name": "Checked-in idea inbox source",
            "locator": (examples / "idea_inbox.jsonl").as_uri(),
        }
    if source_type in {"web_page", "browser_page"}:
        return {
            "kind": SourceKind.LOCAL_FILE,
            "name": "Checked-in browser page source",
            "locator": (examples / "browser_watcher_page.html").as_uri(),
        }
    if source_type in {"repo", "repo_state"}:
        return {
            "kind": SourceKind.REPO_STATE,
            "name": "Current repository state source",
            "locator": str(repo_root),
        }
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
