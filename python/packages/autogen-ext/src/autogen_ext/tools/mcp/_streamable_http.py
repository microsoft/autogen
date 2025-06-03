from autogen_core import Component
from mcp import ClientSession, Tool
from pydantic import BaseModel
from typing_extensions import Self

from ._base import McpToolAdapter
from ._config import StreamableHttpServerParams


class StreamableHttpMcpToolAdapterConfig(BaseModel):
    """Configuration for the MCP tool adapter."""

    server_params: StreamableHttpServerParams
    tool: Tool


class StreamableHttpMcpToolAdapter(
    McpToolAdapter[StreamableHttpServerParams],
    Component[StreamableHttpMcpToolAdapterConfig],
):
    """
    Allows you to wrap an MCP tool running over Streamable HTTP and make it available to AutoGen.

    This adapter enables using MCP-compatible tools that communicate over Streamable HTTP
    with AutoGen agents. Common use cases include integrating with remote MCP services,
    cloud-based tools, and web APIs that implement the Model Context Protocol (MCP).

    .. note::

        To use this class, you need to install `mcp` extra for the `autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mcp]"


    Args:
        server_params (StreamableHttpServerParams): Parameters for the MCP server connection,
            including URL, headers, and timeouts.
        tool (Tool): The MCP tool to wrap.
        session (ClientSession, optional): The MCP client session to use. If not provided,
            it will create a new session. This is useful for testing or when you want to
            manage the session lifecycle yourself.

    Examples:
        Use a remote translation service that implements MCP over Streamable HTTP to
        create tools that allow AutoGen agents to perform translations:

        .. code-block:: python

            import asyncio
            from datetime import timedelta
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StreamableHttpMcpToolAdapter, StreamableHttpServerParams
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken


            async def main() -> None:
                # Create server params for the remote MCP service
                server_params = StreamableHttpServerParams(
                    url="https://api.example.com/mcp",
                    headers={"Authorization": "Bearer your-api-key", "Content-Type": "application/json"},
                    timeout=timedelta(seconds=30),
                    sse_read_timeout=timedelta(seconds=60 * 5),
                    terminate_on_close=True,
                )

                # Get the translation tool from the server
                adapter = await StreamableHttpMcpToolAdapter.from_server_params(server_params, "translate")

                # Create an agent that can use the translation tool
                model_client = OpenAIChatCompletionClient(model="gpt-4")
                agent = AssistantAgent(
                    name="translator",
                    model_client=model_client,
                    tools=[adapter],
                    system_message="You are a helpful translation assistant.",
                )

                # Let the agent translate some text
                await Console(
                    agent.run_stream(task="Translate 'Hello, how are you?' to Spanish", cancellation_token=CancellationToken())
                )


            if __name__ == "__main__":
                asyncio.run(main())

    """

    component_config_schema = StreamableHttpMcpToolAdapterConfig
    component_provider_override = "autogen_ext.tools.mcp.StreamableHttpMcpToolAdapter"

    def __init__(
        self, server_params: StreamableHttpServerParams, tool: Tool, session: ClientSession | None = None
    ) -> None:
        super().__init__(server_params=server_params, tool=tool, session=session)

    def _to_config(self) -> StreamableHttpMcpToolAdapterConfig:
        """
        Convert the adapter to its configuration representation.

        Returns:
            StreamableHttpMcpToolAdapterConfig: The configuration of the adapter.
        """
        return StreamableHttpMcpToolAdapterConfig(server_params=self._server_params, tool=self._tool)

    @classmethod
    def _from_config(cls, config: StreamableHttpMcpToolAdapterConfig) -> Self:
        """
        Create an instance of StreamableHttpMcpToolAdapter from its configuration.

        Args:
            config (StreamableHttpMcpToolAdapterConfig): The configuration of the adapter.

        Returns:
            StreamableHttpMcpToolAdapter: An instance of StreamableHttpMcpToolAdapter.
        """
        return cls(server_params=config.server_params, tool=config.tool)
