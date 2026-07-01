from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from agentic.approvals.service import ApprovalService
from agentic.approvals.store import ApprovalStore
from agentic.connectors import CapabilityKind, ConnectorCapability, ConnectorRegistry
from agentic.connectors.base import ConnectorError
from agentic.connectors.mcp_client import MCPClientConnector, MCPServerConfig
from agentic.connectors.tool_bridge import ConnectorToolBridge
from agentic.policy import PolicyEngine


class Milestone4ConnectorTests(unittest.TestCase):
    def test_local_test_connector_exposes_capabilities(self) -> None:
        registry = ConnectorRegistry([LocalTestConnector()])

        tools = registry.list_capabilities(CapabilityKind.TOOL)
        resources = registry.list_capabilities(CapabilityKind.RESOURCE)
        prompts = registry.list_capabilities(CapabilityKind.PROMPT)

        self.assertEqual(tools[0].name, "echo")
        self.assertEqual(resources[0].name, "resource://local-test/readme")
        self.assertEqual(prompts[0].name, "summarize")

    def test_connector_tool_goes_through_policy_bridge_and_requests_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = ConnectorToolBridge(
                registry=ConnectorRegistry([LocalTestConnector()]),
                policy=PolicyEngine(),
                approvals=ApprovalService(ApprovalStore(Path(tmpdir) / "approvals.jsonl")),
            )

            result = bridge.call_tool("local-test", "echo", {"text": "hello"})

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "approval_required")
        self.assertTrue(result.approval_id)

    def test_unknown_connector_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            class ExternalConnector(LocalTestConnector):
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

    def test_mcp_stdio_connector_discovers_and_calls_local_fixture_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server = Path(tmpdir) / "local_mcp_fixture.py"
            server.write_text(_LOCAL_MCP_FIXTURE_SERVER, encoding="utf-8")
            connector = MCPClientConnector(
                MCPServerConfig(
                    connector_id="mcp-local-fixture",
                    command=(sys.executable, str(server)),
                )
            )
            try:
                tools = connector.list_tools()
                result = connector.call_tool("echo", {"text": "hi"})
                resource = connector.read_resource("resource://local-fixture")
                prompt = connector.get_prompt("summarize", {})
            finally:
                connector.close()

        self.assertEqual(tools[0].name, "echo")
        self.assertEqual(result["content"][0]["text"], "hi")
        self.assertIn("content", resource)
        self.assertIn("messages", prompt)


class LocalTestConnector:
    connector_id = "local-test"

    def list_tools(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.TOOL,
                name="echo",
                description="Echo text through a local test connector.",
                input_schema={"type": "object"},
                source_connector=self.connector_id,
            )
        ]

    def list_resources(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.RESOURCE,
                name="resource://local-test/readme",
                description="Local test read-only resource.",
                source_connector=self.connector_id,
            )
        ]

    def list_prompts(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.PROMPT,
                name="summarize",
                description="Summarization prompt.",
                source_connector=self.connector_id,
            )
        ]

    def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if name != "echo":
            raise ConnectorError(f"unknown local test tool: {name}")
        return {"echo": arguments.get("text", "")}

    def read_resource(self, uri: str) -> object:
        if uri != "resource://local-test/readme":
            raise ConnectorError(f"unknown local test resource: {uri}")
        return {"uri": uri, "content_text": "local test resource content"}

    def get_prompt(self, name: str, arguments: dict[str, object] | None = None) -> str:
        if name != "summarize":
            raise ConnectorError(f"unknown local test prompt: {name}")
        return "Summarize the provided resource."


_LOCAL_MCP_FIXTURE_SERVER = r'''
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
        result = {"resources": [{"uri": "resource://local-fixture", "description": "Local fixture"}]}
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
