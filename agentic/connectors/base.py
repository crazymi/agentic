from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class CapabilityKind(StrEnum):
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"


@dataclass(frozen=True)
class ConnectorCapability:
    kind: CapabilityKind
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    source_connector: str = ""
    requires_approval: bool = False

    @property
    def capability_id(self) -> str:
        return f"{self.source_connector}:{self.kind.value}:{self.name}"


class Connector(Protocol):
    connector_id: str

    def list_tools(self) -> list[ConnectorCapability]:
        ...

    def list_resources(self) -> list[ConnectorCapability]:
        ...

    def list_prompts(self) -> list[ConnectorCapability]:
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        ...

    def read_resource(self, uri: str) -> Any:
        ...

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        ...


class ConnectorError(RuntimeError):
    pass
