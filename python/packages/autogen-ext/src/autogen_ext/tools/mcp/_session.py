from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

import httpx2
from mcp import ClientSession
from mcp.client.session import ElicitationFnT, ListRootsFnT, SamplingFnT
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared._httpx_utils import create_mcp_http_client

from ._config import McpServerParams, SseServerParams, StdioServerParams, StreamableHttpServerParams


def _create_http_client_factory(ssl_verify: bool) -> McpHttpClientFactory:
    """Create an HTTP client factory with the given SSL verification setting."""

    def factory(
        headers: dict[str, Any] | None = None,
        timeout: httpx2.Timeout | None = None,
        auth: httpx2.Auth | None = None,
    ) -> httpx2.AsyncClient:
        kwargs: dict[str, Any] = {"follow_redirects": True, "verify": ssl_verify}
        if timeout is None:
            kwargs["timeout"] = httpx2.Timeout(30.0, read=300.0)
        else:
            kwargs["timeout"] = timeout
        if headers is not None:
            kwargs["headers"] = headers
        if auth is not None:
            kwargs["auth"] = auth
        return httpx2.AsyncClient(**kwargs)

    return factory


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
                read_timeout_seconds=timedelta(seconds=server_params.read_timeout_seconds),
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
    elif isinstance(server_params, SseServerParams):
        async with sse_client(
            url=server_params.url,
            headers=server_params.headers,
            timeout=server_params.timeout,
            sse_read_timeout=server_params.sse_read_timeout,
            httpx_client_factory=_create_http_client_factory(server_params.ssl_verify),
        ) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.sse_read_timeout),
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
    elif isinstance(server_params, StreamableHttpServerParams):
        http_client = httpx2.AsyncClient(
            follow_redirects=True,
            verify=server_params.ssl_verify,
            timeout=httpx2.Timeout(server_params.timeout, read=server_params.sse_read_timeout),
        )
        async with streamablehttp_client(
            url=server_params.url,
            http_client=http_client,
            terminate_on_close=server_params.terminate_on_close,
        ) as (
            read,
            write,
            session_id_callback,  # type: ignore[assignment, unused-variable]
        ):
            # TODO: Handle session_id_callback if needed
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.sse_read_timeout),
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
            ) as session:
                yield session
