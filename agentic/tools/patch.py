from __future__ import annotations

from pathlib import Path
from typing import Any


def apply_patch_text(input: str, *, root: Path) -> dict[str, Any]:
    lines = input.splitlines()
    if not lines or lines[0] != "*** Begin Patch":
        raise ValueError("patch must start with *** Begin Patch")
    if lines[-1] != "*** End Patch":
        raise ValueError("patch must end with *** End Patch")

    index = 1
    changed: list[str] = []
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            index = _apply_add(lines, index, root, changed)
        elif line.startswith("*** Delete File: "):
            path = _resolve(root, line.removeprefix("*** Delete File: "))
            path.unlink()
            changed.append(str(path))
            index += 1
        elif line.startswith("*** Update File: "):
            index = _apply_update(lines, index, root, changed)
        elif not line.strip():
            index += 1
        else:
            raise ValueError(f"unsupported patch line: {line}")
    return {"ok": True, "changed_files": changed, "count": len(changed)}


def _apply_add(lines: list[str], index: int, root: Path, changed: list[str]) -> int:
    path = _resolve(root, lines[index].removeprefix("*** Add File: "))
    index += 1
    content: list[str] = []
    while index < len(lines) and not lines[index].startswith("*** "):
        line = lines[index]
        if not line.startswith("+"):
            raise ValueError("add file lines must start with +")
        content.append(line[1:])
        index += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(content) + ("\n" if content else ""), encoding="utf-8")
    changed.append(str(path))
    return index


def _apply_update(lines: list[str], index: int, root: Path, changed: list[str]) -> int:
    source = _resolve(root, lines[index].removeprefix("*** Update File: "))
    target = source
    index += 1
    if index < len(lines) and lines[index].startswith("*** Move to: "):
        target = _resolve(root, lines[index].removeprefix("*** Move to: "))
        index += 1

    original = source.read_text(encoding="utf-8")
    body: list[str] = []
    while index < len(lines) and not lines[index].startswith("*** "):
        line = lines[index]
        if line.startswith("@@"):
            index += 1
            continue
        body.append(line)
        index += 1

    updated = _apply_line_patch(original, body)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding="utf-8")
    if target != source:
        source.unlink()
    changed.append(str(target))
    return index


def _apply_line_patch(original: str, body: list[str]) -> str:
    old_lines: list[str] = []
    new_lines: list[str] = []
    for line in body:
        if line == "*** End of File":
            continue
        if not line:
            raise ValueError("patch hunk lines must start with space, +, or -")
        prefix = line[0]
        text = line[1:]
        if prefix == " ":
            old_lines.append(text)
            new_lines.append(text)
        elif prefix == "-":
            old_lines.append(text)
        elif prefix == "+":
            new_lines.append(text)
        else:
            raise ValueError("patch hunk lines must start with space, +, or -")

    old = "\n".join(old_lines)
    new = "\n".join(new_lines)
    if original.endswith("\n") and old:
        old += "\n"
    if original.endswith("\n") and new:
        new += "\n"
    count = original.count(old)
    if count != 1:
        raise ValueError(f"update hunk must match exactly once; matched {count} times")
    return original.replace(old, new, 1)


def _resolve(root: Path, path: str) -> Path:
    target = Path(path.strip())
    if not target.is_absolute():
        target = root / target
    resolved = target.resolve()
    workspace = root.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise ValueError(f"patch path escapes workspace: {path}")
    return resolved
