from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentic.tools.base import ToolSpec


DEFAULT_MAX_BYTES = 128_000
DEFAULT_MAX_RESULTS = 100


def read_file(
    path: str,
    *,
    offset: int = 0,
    limit: int | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    target = _resolve_workspace_path(path, root=root)
    data = target.read_text(encoding="utf-8", errors="replace")
    start = max(0, int(offset or 0))
    requested_limit = DEFAULT_MAX_BYTES if limit is None else max(0, int(limit))
    text = data[start : start + requested_limit]
    return {
        "path": str(target),
        "text": text,
        "offset": start,
        "chars": len(text),
        "total_chars": len(data),
        "truncated": start + requested_limit < len(data),
    }


def write_file(
    path: str,
    content: str,
    *,
    create_parents: bool = True,
    root: str | Path | None = None,
) -> dict[str, Any]:
    target = _resolve_workspace_path(path, root=root)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "bytes": len(content.encode("utf-8")), "ok": True}


def edit_file(
    path: str,
    old_text: str = "",
    new_text: str = "",
    *,
    edits: list[dict[str, str]] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    target = _resolve_workspace_path(path, root=root)
    original = target.read_text(encoding="utf-8")
    selected_edits = edits or [{"old_text": old_text, "new_text": new_text}]
    updated = original
    applied = 0
    for edit in selected_edits:
        old = str(edit.get("old_text", ""))
        new = str(edit.get("new_text", ""))
        if not old:
            raise ValueError("edit_file requires non-empty old_text")
        count = updated.count(old)
        if count != 1:
            raise ValueError(f"old_text must match exactly once; matched {count} times")
        updated = updated.replace(old, new, 1)
        applied += 1
    if updated == original:
        return {"path": str(target), "applied": 0, "changed": False}
    target.write_text(updated, encoding="utf-8")
    return {"path": str(target), "applied": applied, "changed": True}


def list_files(
    path: str = ".",
    *,
    recursive: bool = False,
    include_dirs: bool = True,
    limit: int = DEFAULT_MAX_RESULTS,
    root: str | Path | None = None,
) -> dict[str, Any]:
    base = _resolve_workspace_path(path, root=root)
    if not base.exists():
        raise FileNotFoundError(str(base))
    if base.is_file():
        items = [base]
    else:
        iterator = base.rglob("*") if recursive else base.iterdir()
        items = sorted(iterator, key=lambda item: str(item))
    selected: list[dict[str, Any]] = []
    max_items = max(1, min(int(limit or DEFAULT_MAX_RESULTS), 1000))
    for item in items:
        if item.is_dir() and not include_dirs:
            continue
        selected.append(
            {
                "path": str(item),
                "relative_path": str(item.relative_to(_workspace_root(root))),
                "type": "directory" if item.is_dir() else "file",
            }
        )
        if len(selected) >= max_items:
            break
    return {"path": str(base), "items": selected, "count": len(selected), "truncated": len(selected) >= max_items}


def search_files(
    query: str,
    *,
    path: str = ".",
    glob: str = "*",
    regex: bool = False,
    limit: int = DEFAULT_MAX_RESULTS,
    root: str | Path | None = None,
) -> dict[str, Any]:
    if not query:
        raise ValueError("search_files requires query")
    base = _resolve_workspace_path(path, root=root)
    pattern = re.compile(query) if regex else None
    max_items = max(1, min(int(limit or DEFAULT_MAX_RESULTS), 1000))
    matches: list[dict[str, Any]] = []
    for item in sorted(base.rglob(glob), key=lambda candidate: str(candidate)):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            found = bool(pattern.search(line)) if pattern else query in line
            if not found:
                continue
            matches.append(
                {
                    "path": str(item),
                    "relative_path": str(item.relative_to(_workspace_root(root))),
                    "line": line_no,
                    "text": line[:500],
                }
            )
            if len(matches) >= max_items:
                return {"matches": matches, "count": len(matches), "truncated": True}
    return {"matches": matches, "count": len(matches), "truncated": False}


def apply_patch_tool(input: str, *, root: str | Path | None = None) -> dict[str, Any]:
    from agentic.tools.patch import apply_patch_text

    return apply_patch_text(input, root=_workspace_root(root))


def _workspace_root(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path.cwd().resolve()


def _resolve_workspace_path(path: str, *, root: str | Path | None = None) -> Path:
    workspace = _workspace_root(root)
    target = Path(path)
    if not target.is_absolute():
        target = workspace / target
    resolved = target.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise ValueError(f"path escapes workspace: {path}")
    return resolved


READ_FILE_TOOL = ToolSpec(
    name="read_file",
    description="Read a UTF-8 text file from the workspace with optional character offset and limit.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer"},
            "limit": {"type": "integer"},
        },
        "required": ["path"],
    },
    fn=read_file,
)

WRITE_FILE_TOOL = ToolSpec(
    name="write_file",
    description="Create or overwrite a UTF-8 text file inside the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "create_parents": {"type": "boolean"},
        },
        "required": ["path", "content"],
    },
    fn=write_file,
)

EDIT_FILE_TOOL = ToolSpec(
    name="edit_file",
    description="Edit one file using exact text replacement. Each old_text must match exactly once.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
            "edits": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["path"],
    },
    fn=edit_file,
)

LIST_FILES_TOOL = ToolSpec(
    name="list_files",
    description="List files and directories inside the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "recursive": {"type": "boolean"},
            "include_dirs": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    },
    fn=list_files,
)

SEARCH_FILES_TOOL = ToolSpec(
    name="search_files",
    description="Search workspace text files for a literal string or regular expression.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "path": {"type": "string"},
            "glob": {"type": "string"},
            "regex": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    },
    fn=search_files,
)

APPLY_PATCH_TOOL = ToolSpec(
    name="apply_patch",
    description="Apply a structured patch envelope inside the workspace.",
    parameters={
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    },
    fn=apply_patch_tool,
)
