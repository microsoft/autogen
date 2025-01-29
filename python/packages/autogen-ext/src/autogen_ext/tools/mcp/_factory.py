from ._config import McpServerParams, SseServerParams, StdioServerParams
from ._session import create_mcp_server_session
from ._sse import SseMcpToolAdapter
from ._stdio import StdioMcpToolAdapter


async def mcp_server_tools(
    server_params: McpServerParams,
) -> list[StdioMcpToolAdapter | SseMcpToolAdapter]:
    """Create a list of MCP tool adapters for the given server parameters."""
    async with create_mcp_server_session(server_params) as session:
        await session.initialize()

        tools = await session.list_tools()

    if isinstance(server_params, StdioServerParams):
        return [
            StdioMcpToolAdapter(server_params=server_params, tool=tool)
            for tool in tools.tools
        ]
    elif isinstance(server_params, SseServerParams):
        return [
            SseMcpToolAdapter(server_params=server_params, tool=tool)
            for tool in tools.tools
        ]
