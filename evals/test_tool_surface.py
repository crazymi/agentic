from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.policy import PolicyEngine
from agentic.runtime.approval_bridge import ApprovalToolBridge
from agentic.runtime.tool_bridge import ToolBridge
from agentic.tools.execution import exec_command, process, python_execute
from agentic.tools.filesystem import (
    apply_patch_tool,
    edit_file,
    list_files,
    read_file,
    search_files,
    write_file,
)
from agentic.tools.registry import ToolRegistry
from agentic.tools.web_search import web_search


class ToolSurfaceTests(unittest.TestCase):
    def test_default_registry_includes_openclaw_style_tools_and_web_search(self) -> None:
        names = {schema["name"] for schema in ToolRegistry.with_defaults().schemas()}

        self.assertTrue(
            {
                "read_file",
                "write_file",
                "edit_file",
                "apply_patch",
                "list_files",
                "search_files",
                "exec",
                "process",
                "python_execute",
                "web_search",
            }.issubset(names)
        )

    def test_file_tools_read_write_edit_list_and_search_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            write_file("notes/a.txt", "hello\nworld\n", root=tmpdir)
            edit_file("notes/a.txt", "hello", "hi", root=tmpdir)

            read = read_file("notes/a.txt", root=tmpdir)
            listed = list_files("notes", root=tmpdir)
            searched = search_files("world", root=tmpdir)

        self.assertEqual(read["text"], "hi\nworld\n")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(searched["matches"][0]["line"], 2)

    def test_file_tools_reject_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "escapes workspace"):
                read_file("../outside.txt", root=tmpdir)

    def test_apply_patch_tool_adds_and_updates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            added = apply_patch_tool(
                "*** Begin Patch\n"
                "*** Add File: a.txt\n"
                "+one\n"
                "+two\n"
                "*** End Patch",
                root=tmpdir,
            )
            updated = apply_patch_tool(
                "*** Begin Patch\n"
                "*** Update File: a.txt\n"
                "@@\n"
                "-one\n"
                "+ONE\n"
                " two\n"
                "*** End Patch",
                root=tmpdir,
            )
            text = Path(tmpdir, "a.txt").read_text(encoding="utf-8")

        self.assertTrue(added["ok"])
        self.assertTrue(updated["ok"])
        self.assertEqual(text, "ONE\ntwo\n")

    def test_exec_and_python_execute_return_output(self) -> None:
        command_result = exec_command("printf hello", timeout_s=2)
        python_result = python_execute("print(2 + 3)", timeout_s=2)

        self.assertEqual(command_result["stdout"], "hello")
        self.assertEqual(python_result["stdout"], "5\n")

    def test_process_start_and_poll(self) -> None:
        started = process("start", command="printf done")
        polled = process("poll", process_id=started["process_id"])

        self.assertEqual(started["status"], "running")
        self.assertIn(polled["status"], {"running", "exited"})

    def test_web_search_missing_api_key_is_clear_tool_failure(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = ToolBridge().execute_tool_call_text(
                json.dumps(
                    {
                        "tool": "web_search",
                        "arguments": {"query": "agent harness", "provider": "brave"},
                    }
                )
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertIn("missing_api_key", result.error_message or "")

    def test_web_search_normalizes_brave_results(self) -> None:
        def fake_get_json(url, headers):
            self.assertIn("api.search.brave.com", url)
            self.assertEqual(headers["X-Subscription-Token"], "brave-key")
            return {
                "web": {
                    "results": [
                        {
                            "title": "Result",
                            "url": "https://example.com",
                            "description": "Snippet",
                            "age": "2026-07-02",
                        }
                    ]
                }
            }

        with patch.dict("os.environ", {"BRAVE_API_KEY": "brave-key"}, clear=True):
            with patch("agentic.tools.web_search._get_json", fake_get_json):
                result = web_search("agent harness", provider="brave", count=1)

        self.assertEqual(result["provider"], "brave")
        self.assertEqual(result["results"][0]["url"], "https://example.com")
        self.assertEqual(result["results"][0]["source"], "brave")

    def test_approval_bridge_requires_approval_for_mutating_new_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = ApprovalToolBridge(
                tool_bridge=ToolBridge(),
                policy=PolicyEngine(),
                approvals=ApprovalService(ApprovalStore(Path(tmpdir) / "approvals.jsonl")),
            )

            result = bridge.execute_tool_call_text(
                json.dumps({"tool": "exec", "arguments": {"command": "date"}})
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "approval_required")
        self.assertTrue(result.approval_id)


if __name__ == "__main__":
    unittest.main()
