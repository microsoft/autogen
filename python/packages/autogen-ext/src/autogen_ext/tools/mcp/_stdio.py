from autogen_core import Component
from pydantic import BaseModel
from typing_extensions import Self

from mcp import ClientSession, Tool

from ._base import McpToolAdapter
from ._config import StdioServerParams


class StdioMcpToolAdapterConfig(BaseModel):
    """Configuration for the MCP tool adapter."""

    server_params: StdioServerParams
    tool: Tool
    max_retries: int = 0
    retry_delay: float = 1.0
    raise_on_error: bool = False


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
        server_params (StdioServerParams): Parameters for the MCP server connection,
            including command to run and its arguments
        tool (Tool): The MCP tool to wrap
        session (ClientSession, optional): The MCP client session to use. If not provided,
            a new session will be created. This is useful for testing or when you want to
            manage the session lifecycle yourself.
        max_retries (int, optional): The maximum number of retries for tool execution. Defaults to 0.
        retry_delay (float, optional): The delay in seconds between retries. Defaults to 1.0.
        raise_on_error (bool, optional): Whether to raise an exception on tool error. Defaults to False.

    See :func:`~autogen_ext.tools.mcp.mcp_server_tools` for examples.
    """

    component_config_schema = StdioMcpToolAdapterConfig
    component_provider_override = "autogen_ext.tools.mcp.StdioMcpToolAdapter"

    def __init__(
        self,
        server_params: StdioServerParams,
        tool: Tool,
        session: ClientSession | None = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        raise_on_error: bool = False,
    ) -> None:
        super().__init__(
            server_params=server_params,
            tool=tool,
            session=session,
            max_retries=max_retries,
            retry_delay=retry_delay,
            raise_on_error=raise_on_error,
        )

    def _to_config(self) -> StdioMcpToolAdapterConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            StdioMcpToolAdapterConfig: The configuration of the adapter.
        """
        return StdioMcpToolAdapterConfig(
            server_params=self._server_params,
            tool=self._tool,
            max_retries=self._max_retries,
            retry_delay=self._retry_delay,
            raise_on_error=self._raise_on_error,
        )

    @classmethod
    def _from_config(cls, config: StdioMcpToolAdapterConfig) -> Self:
        """
        Create an instance of StdioMcpToolAdapter from its configuration.

        Args:
            config (StdioMcpToolAdapterConfig): The configuration of the adapter.

        Returns:
            StdioMcpToolAdapter: An instance of StdioMcpToolAdapter.
        """
        return cls(
            server_params=config.server_params,
            tool=config.tool,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            raise_on_error=config.raise_on_error,
        )
