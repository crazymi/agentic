from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.connectors import CapabilityKind, ConnectorRegistry, FakeConnector
from agentic.connectors.mcp_client import MCPClientConnector, MCPServerConfig
from agentic.connectors.tool_bridge import ConnectorToolBridge
from agentic.policy import PolicyEngine


class Milestone4ConnectorTests(unittest.TestCase):
    def test_fake_connector_exposes_capabilities(self) -> None:
        registry = ConnectorRegistry([FakeConnector()])

        tools = registry.list_capabilities(CapabilityKind.TOOL)
        resources = registry.list_capabilities(CapabilityKind.RESOURCE)
        prompts = registry.list_capabilities(CapabilityKind.PROMPT)

        self.assertEqual(tools[0].name, "echo")
        self.assertEqual(resources[0].name, "resource://fake/readme")
        self.assertEqual(prompts[0].name, "summarize")

    def test_fake_connector_tool_goes_through_policy_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = ConnectorToolBridge(
                registry=ConnectorRegistry([FakeConnector()]),
                policy=PolicyEngine(),
                approvals=ApprovalService(ApprovalStore(Path(tmpdir) / "approvals.jsonl")),
            )

            result = bridge.call_tool("fake", "echo", {"text": "hello"})

        self.assertTrue(result.ok)
        self.assertEqual(result.result, {"echo": "hello"})

    def test_unknown_connector_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            class ExternalConnector(FakeConnector):
                connector_id = "external"

            bridge = ConnectorToolBridge(
                registry=ConnectorRegistry([ExternalConnector()]),
                policy=PolicyEngine(),
                approvals=ApprovalService(ApprovalStore(Path(tmpdir) / "approvals.jsonl")),
            )

            result = bridge.call_tool("external", "echo", {"text": "hello"})

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "approval_required")
        self.assertTrue(result.approval_id)

    def test_mcp_stdio_connector_discovers_and_calls_fake_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server = Path(tmpdir) / "fake_mcp.py"
            server.write_text(_FAKE_MCP_SERVER, encoding="utf-8")
            connector = MCPClientConnector(
                MCPServerConfig(
                    connector_id="mcp-fake",
                    command=(sys.executable, str(server)),
                )
            )
            try:
                tools = connector.list_tools()
                result = connector.call_tool("echo", {"text": "hi"})
                resource = connector.read_resource("resource://fake")
                prompt = connector.get_prompt("summarize", {})
            finally:
                connector.close()

        self.assertEqual(tools[0].name, "echo")
        self.assertEqual(result["content"][0]["text"], "hi")
        self.assertIn("content", resource)
        self.assertIn("messages", prompt)


_FAKE_MCP_SERVER = r'''
import json, sys
for line in sys.stdin:
    req = json.loads(line)
    method = req.get("method")
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {}}
    elif method == "tools/list":
        result = {"tools": [{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": req["params"]["arguments"].get("text", "")}]}
    elif method == "resources/list":
        result = {"resources": [{"uri": "resource://fake", "description": "Fake"}]}
    elif method == "resources/read":
        result = {"content": [{"uri": req["params"]["uri"], "text": "resource text"}]}
    elif method == "prompts/list":
        result = {"prompts": [{"name": "summarize", "description": "Summarize"}]}
    elif method == "prompts/get":
        result = {"messages": [{"role": "user", "content": {"type": "text", "text": "summarize"}}]}
    else:
        result = {}
    print(json.dumps({"jsonrpc": "2.0", "id": req.get("id"), "result": result}), flush=True)
'''


if __name__ == "__main__":
    unittest.main()
