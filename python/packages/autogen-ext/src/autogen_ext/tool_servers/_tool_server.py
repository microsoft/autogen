
from autogen_core import ComponentBase, Component
from typing import Protocol
from abc import ABC
from pydantic import BaseModel

class ToolServerDiscovery(Protocol):
    async def discover_tools(self) -> list[Component]:
        ...

class ToolServer(ABC, ToolServerDiscovery, ComponentBase[BaseModel]):
    component_type = "tool_server"
