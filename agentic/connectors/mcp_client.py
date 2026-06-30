from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from agentic.connectors.base import CapabilityKind, ConnectorCapability, ConnectorError


@dataclass(frozen=True)
class MCPServerConfig:
    connector_id: str
    command: tuple[str, ...]


class MCPClientConnector:
    def __init__(self, config: MCPServerConfig):
        self.connector_id = config.connector_id
        self.command = config.command
        self._next_id = 1
        self._process: subprocess.Popen[str] | None = None
        self._tools: list[ConnectorCapability] = []
        self._resources: list[ConnectorCapability] = []
        self._prompts: list[ConnectorCapability] = []

    def connect(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        self.refresh_capabilities()

    def close(self) -> None:
        if self._process is not None:
            process = self._process
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            self._process = None

    def refresh_capabilities(self) -> None:
        tools = self._request("tools/list", {}).get("tools", [])
        resources = self._request("resources/list", {}).get("resources", [])
        prompts = self._request("prompts/list", {}).get("prompts", [])
        self._tools = [
            ConnectorCapability(
                kind=CapabilityKind.TOOL,
                name=str(item["name"]),
                description=str(item.get("description", "")),
                input_schema=dict(item.get("inputSchema", {})),
                source_connector=self.connector_id,
            )
            for item in tools
        ]
        self._resources = [
            ConnectorCapability(
                kind=CapabilityKind.RESOURCE,
                name=str(item["uri"]),
                description=str(item.get("description", "")),
                source_connector=self.connector_id,
            )
            for item in resources
        ]
        self._prompts = [
            ConnectorCapability(
                kind=CapabilityKind.PROMPT,
                name=str(item["name"]),
                description=str(item.get("description", "")),
                input_schema=dict(item.get("arguments", {})),
                source_connector=self.connector_id,
            )
            for item in prompts
        ]

    def list_tools(self) -> list[ConnectorCapability]:
        self.connect()
        return list(self._tools)

    def list_resources(self) -> list[ConnectorCapability]:
        self.connect()
        return list(self._resources)

    def list_prompts(self) -> list[ConnectorCapability]:
        self.connect()
        return list(self._prompts)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.connect()
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def read_resource(self, uri: str) -> Any:
        self.connect()
        return self._request("resources/read", {"uri": uri})

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        self.connect()
        result = self._request("prompts/get", {"name": name, "arguments": arguments or {}})
        return json.dumps(result, ensure_ascii=False)

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise ConnectorError("MCP process is not connected")
        request_id = self._next_id
        self._next_id += 1
        process.stdin.write(
            json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                ensure_ascii=False,
            )
            + "\n"
        )
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            raise ConnectorError("MCP process closed")
        response = json.loads(line)
        if "error" in response:
            raise ConnectorError(str(response["error"]))
        return dict(response.get("result", {}))
