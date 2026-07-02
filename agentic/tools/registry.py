from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic.tools.add import ADD_TOOL
from agentic.tools.base import ToolSpec
from agentic.tools.execution import EXEC_TOOL, PROCESS_TOOL, PYTHON_EXECUTE_TOOL
from agentic.tools.filesystem import (
    APPLY_PATCH_TOOL,
    EDIT_FILE_TOOL,
    LIST_FILES_TOOL,
    READ_FILE_TOOL,
    SEARCH_FILES_TOOL,
    WRITE_FILE_TOOL,
)
from agentic.tools.parser import ToolCall
from agentic.tools.skill_workshop import skill_workshop_tool
from agentic.tools.source_discovery import source_candidate_tool
from agentic.tools.web import HTML_EXTRACT_LINKS_TOOL, WEB_FETCH_TOOL
from agentic.tools.web_search import WEB_SEARCH_TOOL
from agentic.tools.workflow_spec import workflow_spec_tool


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec] | None = None):
        self._tools = {tool.name: tool for tool in (tools or [])}

    @classmethod
    def with_defaults(cls, *, state_dir: str | Path | None = None) -> "ToolRegistry":
        state_root = Path(state_dir) if state_dir else None
        skill_workshop_db = state_root / "skill_workshop.sqlite3" if state_root else None
        workflow_db = state_root / "workflows.sqlite3" if state_root else None
        skill_workshop = (
            skill_workshop_tool(skill_workshop_db)
            if skill_workshop_db is not None
            else skill_workshop_tool()
        )
        workflow_spec = (
            workflow_spec_tool(workflow_db)
            if workflow_db is not None
            else workflow_spec_tool()
        )
        source_candidate = (
            source_candidate_tool(state_root)
            if state_root is not None
            else source_candidate_tool()
        )
        return cls(
            [
                ADD_TOOL,
                READ_FILE_TOOL,
                WRITE_FILE_TOOL,
                EDIT_FILE_TOOL,
                APPLY_PATCH_TOOL,
                LIST_FILES_TOOL,
                SEARCH_FILES_TOOL,
                EXEC_TOOL,
                PROCESS_TOOL,
                PYTHON_EXECUTE_TOOL,
                WEB_FETCH_TOOL,
                HTML_EXTRACT_LINKS_TOOL,
                WEB_SEARCH_TOOL,
                source_candidate,
                skill_workshop,
                workflow_spec,
            ]
        )

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def schema_names(self, names: list[str]) -> list[dict[str, Any]]:
        return [self._tools[name].schema() for name in names if name in self._tools]

    def execute(self, call: ToolCall) -> Any:
        if call.tool not in self._tools:
            raise KeyError(f"unknown tool: {call.tool}")
        return self._tools[call.tool].fn(**call.arguments)
