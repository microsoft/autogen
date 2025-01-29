from typing import Self

from autogen_core import Component
from mcp import Tool
from pydantic import BaseModel

from ._base import McpToolAdapter
from ._config import StdioServerParams


class StdioMcpToolAdapterConfig(BaseModel):
    """Configuration for the MCP tool adapter."""

    server_params: StdioServerParams
    tool: Tool


class StdioMcpToolAdapter(
    McpToolAdapter[StdioServerParams],
    Component[StdioMcpToolAdapterConfig],
):
    """
    Adapter for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (StdioServerParameters): Parameters for the MCP server connection.
        tool (Tool): The MCP tool to wrap.
    """

    component_config_schema = StdioMcpToolAdapterConfig
    component_provider_override = "autogen-ext.tools.mcp.StdioMcpToolAdapter"

    def __init__(self, server_params: StdioServerParams, tool: Tool) -> None:
        super().__init__(server_params=server_params, tool=tool)

    def _to_config(self) -> StdioMcpToolAdapterConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            StdioMcpToolAdapterConfig: The configuration of the adapter.
        """
        return StdioMcpToolAdapterConfig(server_params=self._server_params, tool=self._tool)

    @classmethod
    def _from_config(cls, config: StdioMcpToolAdapterConfig) -> Self:
        """
        Create an instance of StdioMcpToolAdapter from its configuration.

        Args:
            config (StdioMcpToolAdapterConfig): The configuration of the adapter.

        Returns:
            StdioMcpToolAdapter: An instance of StdioMcpToolAdapter.
        """
        return cls(server_params=config.server_params, tool=config.tool)
