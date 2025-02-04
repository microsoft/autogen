from autogen_core import Component
from mcp import Tool
from pydantic import BaseModel
from typing_extensions import Self

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
    """Allows you to wrap an MCP tool running over STDIO and make it available to AutoGen.

    This adapter enables using MCP-compatible tools that communicate over standard input/output
    with AutoGen agents. Common use cases include wrapping command-line tools and local services
    that implement the Model Context Protocol (MCP).

    Args:
        server_params (StdioServerParams): Parameters for the MCP server connection,
            including command to run and its arguments
        tool (Tool): The MCP tool to wrap

    Examples:
        Use the FileSystem MCP server to create tools that allow AutoGen agents to interact
        with the local filesystem:

        .. code-block:: python

            import asyncio
            from pathlib import Path
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StdioMcpToolAdapter, StdioServerParams
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken


            async def main() -> None:
                # Get desktop path cross-platform
                desktop_path = str(Path.home() / "Desktop")

                # Create server params for the FileSystem MCP server
                server_params = StdioServerParams(
                    command="npx.cmd",  # Use npx on Windows
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        desktop_path,
                    ],
                )

                # Get all available tools from the server
                tools = await mcp_server_tools(server_params)

                # Create an agent that can use the filesystem tools
                model_client = OpenAIChatCompletionClient(model="gpt-4")
                agent = AssistantAgent(
                    name="file_manager",
                    model_client=model_client,
                    tools=tools,
                )

                # Let the agent create and write to a file
                await Console(
                    agent.run_stream(
                        task="Create a file called 'hello.txt' with the content 'Hello, World!'",
                        cancellation_token=CancellationToken(),
                    )
                )


            if __name__ == "__main__":
                asyncio.run(main())

    """

    component_config_schema = StdioMcpToolAdapterConfig
    component_provider_override = "autogen_ext.tools.mcp.StdioMcpToolAdapter"

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
