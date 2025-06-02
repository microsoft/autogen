from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from ._config import McpServerParams, SseServerParams, StdioServerParams, StreamableHttpServerParams


@asynccontextmanager
async def create_mcp_server_session(
    server_params: McpServerParams,
) -> AsyncGenerator[ClientSession, None]:
    """Create an MCP client session for the given server parameters."""
    if isinstance(server_params, StdioServerParams):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.read_timeout_seconds),
            ) as session:
                yield session
    elif isinstance(server_params, SseServerParams):
        async with sse_client(**server_params.model_dump(exclude={"type"})) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.sse_read_timeout),
            ) as session:
                yield session
    elif isinstance(server_params, StreamableHttpServerParams):
        async with streamablehttp_client(**server_params.model_dump(exclude={"type"})) as (
            read,
            write,
            session_id_callback,
        ):
            # TODO: Handle session_id_callback if needed
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=server_params.sse_read_timeout,
            ) as session:
                yield session
