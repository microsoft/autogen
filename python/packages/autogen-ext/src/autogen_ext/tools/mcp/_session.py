from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx2

from mcp import ClientSession
from mcp.client.session import ElicitationFnT, ListRootsFnT, SamplingFnT
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from ._config import McpServerParams, SseServerParams, StdioServerParams, StreamableHttpServerParams


@asynccontextmanager
async def create_mcp_server_session(
    server_params: McpServerParams,
    sampling_callback: SamplingFnT | None = None,
    elicitation_callback: ElicitationFnT | None = None,
    list_roots_callback: ListRootsFnT | None = None,
) -> AsyncGenerator[ClientSession, None]:
    """Create an MCP client session for the given server parameters."""
    if isinstance(server_params, StdioServerParams):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=server_params.read_timeout_seconds,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
    elif isinstance(server_params, SseServerParams):
        async with sse_client(**server_params.model_dump(exclude={"type"})) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=server_params.sse_read_timeout,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
    elif isinstance(server_params, StreamableHttpServerParams):
        # mcp 2.x dropped the timeout kwargs from streamable_http_client; HTTP
        # timeouts and headers are configured on the httpx2 client instead.
        timeout = httpx2.Timeout(server_params.timeout, read=server_params.sse_read_timeout)
        http_client = create_mcp_http_client(headers=server_params.headers, timeout=timeout)

        async with streamable_http_client(
            url=server_params.url,
            http_client=http_client,
            terminate_on_close=server_params.terminate_on_close,
        ) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=server_params.sse_read_timeout,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
