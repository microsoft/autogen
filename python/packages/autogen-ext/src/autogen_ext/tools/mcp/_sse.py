from autogen_core import Component
from mcp import Tool
from pydantic import BaseModel
from typing_extensions import Self

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
    Allows you to wrap an MCP tool running over Server-Sent Events (SSE) and make it available to AutoGen.

    This adapter enables using MCP-compatible tools that communicate over HTTP with SSE
    with AutoGen agents. Common use cases include integrating with remote MCP services,
    cloud-based tools, and web APIs that implement the Model Context Protocol (MCP).

    .. note::

        To use this class, you need to install `mcp` extra for the `autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mcp]"

    Args:
        server_params (SseServerParameters): Parameters for the MCP server connection,
            including URL, headers, and timeouts
        tool (Tool): The MCP tool to wrap

    Examples:
        Use a remote translation service that implements MCP over SSE to create tools
        that allow AutoGen agents to perform translations:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken


            async def main() -> None:
                # Create server params for the remote MCP service
                server_params = SseServerParams(
                    url="https://api.example.com/mcp",
                    headers={"Authorization": "Bearer your-api-key", "Content-Type": "application/json"},
                    timeout=30,  # Connection timeout in seconds
                )

                # Get the translation tool from the server
                adapter = await SseMcpToolAdapter.from_server_params(server_params, "translate")

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

    component_config_schema = SseMcpToolAdapterConfig
    component_provider_override = "autogen_ext.tools.mcp.SseMcpToolAdapter"

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
