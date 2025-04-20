from abc import ABC
from typing import Protocol

from autogen_core import Component, ComponentBase
from pydantic import BaseModel


class ToolDiscovery(Protocol):
    async def discover_tools(self) -> list[Component]: ...


class ToolServer(ABC, ToolDiscovery, ComponentBase[BaseModel]):
    component_type = "tool_server"
