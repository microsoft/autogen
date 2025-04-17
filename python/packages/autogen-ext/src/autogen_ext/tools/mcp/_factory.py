from mcp import ClientSession

from ._config import McpServerParams, SseServerParams, StdioServerParams
from ._session import create_mcp_server_session
from ._sse import SseMcpToolAdapter
from ._stdio import StdioMcpToolAdapter


async def mcp_server_tools(
    server_params: McpServerParams,
    session: ClientSession | None = None,
) -> list[StdioMcpToolAdapter | SseMcpToolAdapter]:
    """Creates a list of MCP tool adapters that can be used with AutoGen agents.

    This factory function connects to an MCP server and returns adapters for all available tools.
    The adapters can be directly assigned to an AutoGen agent's tools list.

    .. note::

        To use this function, you need to install `mcp` extra for the `autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mcp]"

    Args:
        server_params (McpServerParams): Connection parameters for the MCP server.
            Can be either StdioServerParams for command-line tools or
            SseServerParams for HTTP/SSE services.
        session (ClientSession | None): Optional existing session to use. This is used
            when you want to reuse an existing connection to the MCP server. The session
            will be reused when creating the MCP tool adapters.

    Returns:
        list[StdioMcpToolAdapter | SseMcpToolAdapter]: A list of tool adapters ready to use
            with AutoGen agents.

    Examples:

        **Local file system MCP service over standard I/O example:**

        Install the filesystem server package from npm (requires Node.js 16+ and npm).

        .. code-block:: bash

            npm install -g @modelcontextprotocol/server-filesystem

        Create an agent that can use all tools from the local filesystem MCP server.

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
                    tools=tools,  # type: ignore
                )

                # The agent can now use any of the filesystem tools
                await agent.run(task="Create a file called test.txt with some content", cancellation_token=CancellationToken())


            if __name__ == "__main__":
                asyncio.run(main())

        **Local fetch MCP service over standard I/O example:**

        Install the `mcp-server-fetch` package.

        .. code-block:: bash

            pip install mcp-server-fetch

        Create an agent that can use the `fetch` tool from the local MCP server.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools


            async def main() -> None:
                # Get the fetch tool from mcp-server-fetch.
                fetch_mcp_server = StdioServerParams(command="uvx", args=["mcp-server-fetch"])
                tools = await mcp_server_tools(fetch_mcp_server)

                # Create an agent that can use the fetch tool.
                model_client = OpenAIChatCompletionClient(model="gpt-4o")
                agent = AssistantAgent(name="fetcher", model_client=model_client, tools=tools, reflect_on_tool_use=True)  # type: ignore

                # Let the agent fetch the content of a URL and summarize it.
                result = await agent.run(task="Summarize the content of https://en.wikipedia.org/wiki/Seattle")
                print(result.messages[-1])


            asyncio.run(main())

        **Sharing an MCP client session across multiple tools:**

        You can create a single MCP client session and share it across multiple tools.
        This is sometimes required when the server maintains a session state
        (e.g., a browser state) that should be reused for multiple requests.

        The following example show how to create a single MCP client session
        to a local Playwright server and use it with an agent.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.mcp import StdioServerParams, create_mcp_server_session, mcp_server_tools


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o", parallel_tool_calls=False)  # type: ignore
                params = StdioServerParams(
                    command="npx",
                    args=["@playwright/mcp@latest"],
                    read_timeout_seconds=60,
                )
                async with create_mcp_server_session(params) as session:
                    await session.initialize()
                    tools = await mcp_server_tools(server_params=params, session=session)
                    print(f"Tools: {[tool.name for tool in tools]}")

                    agent = AssistantAgent(
                        name="Assistant",
                        model_client=model_client,
                        tools=tools,  # type: ignore
                    )

                    termination = TextMentionTermination("TERMINATE")
                    team = RoundRobinGroupChat([agent], termination_condition=termination)
                    await Console(
                        team.run_stream(
                            task="Go to https://ekzhu.com/, visit the first link in the page, then tell me about the linked page."
                        )
                    )


            asyncio.run(main())


        **Remote MCP service over SSE example:**

        .. code-block:: python

            from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools


            async def main() -> None:
                # Setup server params for remote service
                server_params = SseServerParams(url="https://api.example.com/mcp", headers={"Authorization": "Bearer token"})

                # Get all available tools
                tools = await mcp_server_tools(server_params)

                # Create an agent with all tools
                agent = AssistantAgent(name="tool_user", model_client=OpenAIChatCompletionClient(model="gpt-4"), tools=tools)  # type: ignore

    For more examples and detailed usage, see the samples directory in the package repository.
    """
    if session is None:
        async with create_mcp_server_session(server_params) as temp_session:
            await temp_session.initialize()

            tools = await temp_session.list_tools()
    else:
        tools = await session.list_tools()

    if isinstance(server_params, StdioServerParams):
        return [StdioMcpToolAdapter(server_params=server_params, tool=tool, session=session) for tool in tools.tools]
    elif isinstance(server_params, SseServerParams):
        return [SseMcpToolAdapter(server_params=server_params, tool=tool, session=session) for tool in tools.tools]
    raise ValueError(f"Unsupported server params type: {type(server_params)}")
