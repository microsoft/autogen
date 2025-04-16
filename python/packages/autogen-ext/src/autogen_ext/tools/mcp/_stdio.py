from autogen_core import Component, ComponentModel
from mcp import Tool
from pydantic import BaseModel
from typing_extensions import Self

from ._base import McpToolAdapter
from ._config import StdioServerParams
from ._session import McpSession


class StdioMcpToolAdapterConfig(BaseModel):
    """Configuration for the MCP tool adapter."""

    session: ComponentModel
    tool: Tool


class StdioMcpToolAdapter(
    McpToolAdapter[StdioServerParams],
    Component[StdioMcpToolAdapterConfig],
):
    """Allows you to wrap an MCP tool running over STDIO and make it available to AutoGen.

    This adapter enables using MCP-compatible tools that communicate over standard input/output
    with AutoGen agents. Common use cases include wrapping command-line tools and local services
    that implement the Model Context Protocol (MCP).

    .. note::

        To use this class, you need to install `mcp` extra for the `autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mcp]"


    Args:
        session (McpSession): The MCP session to use for communication with the server.
        tool (Tool): The MCP tool to wrap

    See :func:`~autogen_ext.tools.mcp.mcp_server_tools` for examples.
    """

    component_config_schema = StdioMcpToolAdapterConfig
    component_provider_override = "autogen_ext.tools.mcp.StdioMcpToolAdapter"

    def __init__(self, session: McpSession, tool: Tool) -> None:
        super().__init__(session=session, tool=tool)

    def _to_config(self) -> StdioMcpToolAdapterConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            StdioMcpToolAdapterConfig: The configuration of the adapter.
        """
        return StdioMcpToolAdapterConfig(session=self._session.dump_component(), tool=self._tool)

    @classmethod
    def _from_config(cls, config: StdioMcpToolAdapterConfig) -> Self:
        """
        Create an instance of StdioMcpToolAdapter from its configuration.

        Args:
            config (StdioMcpToolAdapterConfig): The configuration of the adapter.

        Returns:
            StdioMcpToolAdapter: An instance of StdioMcpToolAdapter.
        """
        return cls(session=McpSession.load_component(config.session), tool=config.tool)
