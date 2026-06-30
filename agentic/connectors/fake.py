from __future__ import annotations

from typing import Any

from agentic.connectors.base import CapabilityKind, ConnectorCapability, ConnectorError


class FakeConnector:
    connector_id = "fake"

    def list_tools(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.TOOL,
                name="echo",
                description="Echo text through a fake connector.",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                source_connector=self.connector_id,
            )
        ]

    def list_resources(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.RESOURCE,
                name="resource://fake/readme",
                description="Fake read-only resource.",
                source_connector=self.connector_id,
            )
        ]

    def list_prompts(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                kind=CapabilityKind.PROMPT,
                name="summarize",
                description="Fake summarization prompt.",
                input_schema={"type": "object"},
                source_connector=self.connector_id,
            )
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name != "echo":
            raise ConnectorError(f"unknown fake tool: {name}")
        return {"echo": arguments.get("text", "")}

    def read_resource(self, uri: str) -> Any:
        if uri != "resource://fake/readme":
            raise ConnectorError(f"unknown fake resource: {uri}")
        return {"uri": uri, "content_text": "fake resource content"}

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if name != "summarize":
            raise ConnectorError(f"unknown fake prompt: {name}")
        return "Summarize the provided resource faithfully."
