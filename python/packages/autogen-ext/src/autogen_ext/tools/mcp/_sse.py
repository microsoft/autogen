from typing import Self

from autogen_core import Component
from mcp import Tool
from pydantic import BaseModel

from ._base import McpToolAdapter
from ._config import SseServerParams


class SseMcpToolAdapterConfig(BaseModel):
    """Configuration for the MCP tool adapter."""

    server_params: SseServerParams
    tool: Tool


class SseMcpToolAdapter(
    McpToolAdapter[SseServerParams],
    Component[SseMcpToolAdapterConfig],
):
    """
    Adapter for MCP tools to make them compatible with AutoGen.

    Args:
        server_params (SseServerParameters): Parameters for the MCP server connection.
        tool (Tool): The MCP tool to wrap.
    """

    component_config_schema = SseMcpToolAdapterConfig
    component_provider_override = "autogen-ext.tools.mcp.SseMcpToolAdapter"

    def __init__(self, server_params: SseServerParams, tool: Tool) -> None:
        super().__init__(server_params=server_params, tool=tool)

    def _to_config(self) -> SseMcpToolAdapterConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            SseMcpToolAdapterConfig: The configuration of the adapter.
        """
        return SseMcpToolAdapterConfig(server_params=self._server_params, tool=self._tool)

    @classmethod
    def _from_config(cls, config: SseMcpToolAdapterConfig) -> Self:
        """
        Create an instance of SseMcpToolAdapter from its configuration.

        Args:
            config (SseMcpToolAdapterConfig): The configuration of the adapter.

        Returns:
            SseMcpToolAdapter: An instance of SseMcpToolAdapter.
        """
        return cls(server_params=config.server_params, tool=config.tool)
