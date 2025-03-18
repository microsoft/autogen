
from autogen_core import ComponentBase, Component
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ToolServer(ABC, ComponentBase[BaseModel]):
    component_type = "tool_server"

    @abstractmethod
    async def discover_tools(self) -> list[Component]:
        ...
