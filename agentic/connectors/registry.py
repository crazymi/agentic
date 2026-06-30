from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.connectors.base import CapabilityKind, Connector, ConnectorCapability


@dataclass(frozen=True)
class ConnectorToolCall:
    connector_id: str
    name: str
    arguments: dict[str, Any]


class ConnectorRegistry:
    def __init__(self, connectors: list[Connector] | None = None):
        self._connectors: dict[str, Connector] = {}
        for connector in connectors or []:
            self.register(connector)

    def register(self, connector: Connector) -> None:
        self._connectors[connector.connector_id] = connector

    def list_connectors(self) -> list[str]:
        return sorted(self._connectors)

    def list_capabilities(
        self,
        kind: CapabilityKind | str | None = None,
    ) -> list[ConnectorCapability]:
        capabilities: list[ConnectorCapability] = []
        for connector in self._connectors.values():
            capabilities.extend(connector.list_tools())
            capabilities.extend(connector.list_resources())
            capabilities.extend(connector.list_prompts())
        if kind is not None:
            selected = CapabilityKind(kind)
            capabilities = [item for item in capabilities if item.kind == selected]
        return capabilities

    def call_tool(self, connector_id: str, name: str, arguments: dict[str, Any]) -> Any:
        return self._connectors[connector_id].call_tool(name, arguments)

    def read_resource(self, connector_id: str, uri: str) -> Any:
        return self._connectors[connector_id].read_resource(uri)

    def get_prompt(
        self,
        connector_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> str:
        return self._connectors[connector_id].get_prompt(name, arguments)

    def find_tool(self, connector_id: str, name: str) -> ConnectorCapability:
        for capability in self._connectors[connector_id].list_tools():
            if capability.name == name:
                return capability
        raise KeyError(f"unknown connector tool: {connector_id}.{name}")
