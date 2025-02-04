from ._config import McpServerParams, SseServerParams, StdioServerParams
from ._session import create_mcp_server_session
from ._sse import SseMcpToolAdapter
from ._stdio import StdioMcpToolAdapter


async def mcp_server_tools(
    server_params: McpServerParams,
) -> list[StdioMcpToolAdapter | SseMcpToolAdapter]:
    """Creates a list of MCP tool adapters that can be used with AutoGen agents.

    This factory function connects to an MCP server and returns adapters for all available tools.
    The adapters can be directly assigned to an AutoGen agent's tools list.

    Args:
        server_params (McpServerParams): Connection parameters for the MCP server.
            Can be either StdioServerParams for command-line tools or
            SseServerParams for HTTP/SSE services.

    Returns:
        list[StdioMcpToolAdapter | SseMcpToolAdapter]: A list of tool adapters ready to use
            with AutoGen agents.

    Examples:
        Create an agent that can use all tools from a local filesystem MCP server:

        .. code-block:: python

            import asyncio
            from pathlib import Path
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
            from autogen_agentchat.agents import AssistantAgent
            from autogen_core import CancellationToken


            async def main() -> None:
                # Setup server params for local filesystem access
                desktop = str(Path.home() / "Desktop")
                server_params = StdioServerParams(
                    command="npx.cmd", args=["-y", "@modelcontextprotocol/server-filesystem", desktop]
                )

                # Get all available tools from the server
                tools = await mcp_server_tools(server_params)

                # Create an agent that can use all the tools
                agent = AssistantAgent(
                    name="file_manager",
                    model_client=OpenAIChatCompletionClient(model="gpt-4"),
                    tools=tools,  # Assign all tools to the agent
                )

                # The agent can now use any of the filesystem tools
                await agent.run(task="Create a file called test.txt with some content", cancellation_token=CancellationToken())


            if __name__ == "__main__":
                asyncio.run(main())

        Or connect to a remote MCP service over SSE:

        .. code-block:: python

            from autogen_ext_mcp.tools import SseServerParams, mcp_server_tools


            async def main() -> None:
                # Setup server params for remote service
                server_params = SseServerParams(url="https://api.example.com/mcp", headers={"Authorization": "Bearer token"})

                # Get all available tools
                tools = await mcp_server_tools(server_params)

                # Create an agent with all tools
                agent = AssistantAgent(name="tool_user", model_client=OpenAIChatCompletionClient(model="gpt-4"), tools=tools)

    For more examples and detailed usage, see the samples directory in the package repository.
    """
    async with create_mcp_server_session(server_params) as session:
        await session.initialize()

        tools = await session.list_tools()

    if isinstance(server_params, StdioServerParams):
        return [StdioMcpToolAdapter(server_params=server_params, tool=tool) for tool in tools.tools]
    elif isinstance(server_params, SseServerParams):
        return [SseMcpToolAdapter(server_params=server_params, tool=tool) for tool in tools.tools]
