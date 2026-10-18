from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

from mcp import ClientSession
from mcp.client.session import ElicitationFnT, ListRootsFnT, SamplingFnT
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

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
                read_timeout_seconds=float(server_params.read_timeout_seconds) if server_params.read_timeout_seconds is not None else None,
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
                read_timeout_seconds=float(server_params.sse_read_timeout) if server_params.sse_read_timeout is not None else None,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
    elif isinstance(server_params, StreamableHttpServerParams):
        # Convert float seconds to timedelta for the streamablehttp_client
        params_dict = server_params.model_dump(exclude={"type", "timeout", "sse_read_timeout"})
        
        import httpx2
        http_client = httpx2.AsyncClient(timeout=float(server_params.timeout))
        params_dict["http_client"] = http_client

        async with streamable_http_client(**params_dict) as (
            read,
            write,
        ):
            # TODO: Handle session_id_callback if needed
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=float(server_params.sse_read_timeout) if server_params.sse_read_timeout is not None else None,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
