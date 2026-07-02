from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentic.skills.models import (
    SkillManifest,
    SkillPackage,
    SkillRequirements,
    SkillTriggers,
)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


class SkillLoadError(ValueError):
    pass


class SkillLoader:
    def __init__(self, root: str | Path = "skills"):
        self.root = Path(root)

    def load_all(self) -> list[SkillPackage]:
        if not self.root.exists():
            return []
        packages = []
        for path in sorted(self.root.glob("*/SKILL.md")):
            package = self.load(path)
            if package.manifest.enabled:
                packages.append(package)
        return packages

    def load(self, path: str | Path) -> SkillPackage:
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        return self.load_text(text, path=path.parent)

    def load_text(self, text: str, *, path: str | Path | None = None) -> SkillPackage:
        package_path = Path(path) if path is not None else self.root
        match = _FRONTMATTER_RE.match(text)
        if match is None:
            raise SkillLoadError(f"skill missing frontmatter: {package_path}")
        raw_manifest = _parse_simple_yaml(match.group(1))
        body = match.group(2).strip()
        manifest = _manifest_from_data(raw_manifest)
        return SkillPackage(path=package_path, manifest=manifest, body=body)


def _manifest_from_data(data: dict[str, Any]) -> SkillManifest:
    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not name:
        raise SkillLoadError("skill manifest requires non-empty name")
    if not isinstance(description, str) or not description:
        raise SkillLoadError("skill manifest requires non-empty description")
    requires = data.get("requires") or {}
    triggers = data.get("triggers") or {}
    return SkillManifest(
        name=name,
        description=description,
        requires=SkillRequirements(
            connectors=list(requires.get("connectors", [])),
            tools=list(requires.get("tools", [])),
            resources=list(requires.get("resources", [])),
        ),
        triggers=SkillTriggers(
            keywords=list(triggers.get("keywords", [])),
            task_kinds=list(triggers.get("task_kinds", [])),
        ),
        enabled=bool(data.get("enabled", True)),
    )


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    current_key = ""
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key, value = _split_key_value(raw_line)
            if value == "":
                current = {}
                current_key = key
                root[key] = current
            else:
                root[key] = _parse_value(value)
                current = None
        elif current is not None:
            key, value = _split_key_value(raw_line.strip())
            current[key] = _parse_value(value)
        else:
            raise SkillLoadError(f"invalid nested frontmatter line: {raw_line}")
    return root


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise SkillLoadError(f"invalid frontmatter line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_value(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return value.strip('"').strip("'")
