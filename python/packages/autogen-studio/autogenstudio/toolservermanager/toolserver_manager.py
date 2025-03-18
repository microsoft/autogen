from typing import Union

from autogen_core import Component, ComponentModel
from autogen_ext.tool_servers import ToolServer


class ToolServerManager:
    """ToolServerManager manages tool servers and tool discovery from those servers."""

    async def _create_tool_server(
        self,
        tool_server_config: Union[dict, ComponentModel],
    ):
        """Create a tool server from the given configuration."""
        if not tool_server_config:
            raise Exception("Tool server config is required")

        if isinstance(tool_server_config, dict):
            config = tool_server_config
        else:
            config = tool_server_config.model_dump()

        try:
            server = ToolServer.load_component(config)
            return server
        except Exception as e:
            raise Exception(f"Failed to create tool server: {e}") from e

    async def discover_tools(self, tool_server_config: Union[dict, ComponentModel]) -> list[Component]:
        """Discover tools from the given tool server."""
        try:
            server = await self._create_tool_server(tool_server_config)
            return await server.discover_tools()
        except Exception as e:
            raise Exception(f"Failed to discover tools: {e}") from e
