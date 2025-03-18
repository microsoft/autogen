from typing import Self
from autogen_ext.tools.mcp._config import StdioServerParams
from autogen_ext.tools.mcp._factory import mcp_server_tools
from autogen_core import Component
from ._tool_server import ToolServer

class StdioMcpToolServerConfig(StdioServerParams):
    pass


class StdioMcpToolServer(ToolServer, Component[StdioMcpToolServerConfig]):
    component_config_schema = StdioMcpToolServerConfig
    component_type = "tool_server"
    component_provider_override = "autogen_ext.tool_servers.StdioMcpToolServer"

    def __init__(self, config: StdioMcpToolServerConfig):
        self.config: StdioMcpToolServerConfig = config

    async def discover_tools(self) -> list[Component]:
        try:
            tools = await mcp_server_tools(self.config)
            return tools
        except Exception as e:
            raise Exception(f"Failed to discover tools: {e}")
    
    def _to_config(self) -> StdioMcpToolServerConfig:
        return StdioMcpToolServerConfig(**self.config.model_dump())
    
    @classmethod
    def _from_config(cls, config: StdioMcpToolServerConfig) -> Self:
        return cls(config)
