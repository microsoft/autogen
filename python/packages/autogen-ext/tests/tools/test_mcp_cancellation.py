"""Regression tests for CancellationToken support in McpWorkbench.call_tool.

McpSessionActor used to hand back the bare coroutine returned by
ClientSession.call_tool (never wrapped in a Task/Future), so
CancellationToken.link_future -- which requires a Future/Task -- raised
AttributeError instead of cancelling the in-flight call.
"""

import asyncio
import atexit
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from mcp import types as mcp_types

# Prevent atexit handlers registered by McpSessionActor from running during the
# test suite's shutdown, matching the convention in test_mcp_actor.py.
original_atexit_register = atexit.register


def _mock_atexit_register(func: Callable[[], None], *args: Any, **kwargs: Any) -> None:
    pass


atexit.register = _mock_atexit_register  # type: ignore[assignment]


def _make_initialize_result() -> mcp_types.InitializeResult:
    return mcp_types.InitializeResult(
        protocolVersion="1.0",
        capabilities=mcp_types.ServerCapabilities(),
        serverInfo=mcp_types.Implementation(name="test", version="1.0"),
    )


async def _cleanup_workbench(workbench: McpWorkbench) -> None:
    """Cancel the actor task directly instead of workbench.stop()/actor.close().

    actor.close() awaits self._actor_task, but _run_actor's own finally clause
    sets self._actor_task to None as it exits, which races close() and can
    raise `TypeError: object NoneType can't be used in 'await' expression`.
    This pre-existing race is unrelated to the cancellation bug under test.
    """
    actor = workbench._actor  # type: ignore[reportPrivateUsage]
    if actor is not None and actor._actor_task is not None:  # type: ignore[reportPrivateUsage]
        actor._actor_task.cancel()  # type: ignore[reportPrivateUsage]
        try:
            await actor._actor_task  # type: ignore[reportPrivateUsage]
        except (asyncio.CancelledError, Exception):
            pass
    # Avoid McpWorkbench.__del__ scheduling an unawaited stop() task at interpreter shutdown.
    workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_call_tool_cancellation_stops_inflight_call() -> None:
    """Cancelling the token while call_tool is in flight must cancel the call, not run it to completion."""
    started = asyncio.Event()

    async def slow_call_tool(name: str, arguments: Any) -> mcp_types.CallToolResult:
        started.set()
        await asyncio.sleep(5)
        return mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text="done")], isError=False)

    @asynccontextmanager
    async def mock_session_ctx(
        server_params: Any,
        sampling_callback: Any = None,
        elicitation_callback: Any = None,
        list_roots_callback: Any = None,
    ) -> AsyncGenerator[MagicMock, None]:
        mock_session = MagicMock()
        mock_session.initialize = AsyncMock(return_value=_make_initialize_result())
        mock_session.call_tool = slow_call_tool
        yield mock_session

    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", mock_session_ctx):
        workbench = McpWorkbench(server_params=StdioServerParams(command="echo", args=["test"]))
        await workbench.start()
        try:
            token = CancellationToken()
            call_task = asyncio.create_task(workbench.call_tool("sleep", {}, cancellation_token=token))

            await asyncio.wait_for(started.wait(), timeout=1.0)

            start = asyncio.get_event_loop().time()
            token.cancel()  # Must not raise AttributeError.

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(call_task, timeout=1.0)
            elapsed = asyncio.get_event_loop().time() - start

            # The call must be cancelled promptly, not run to completion (5s sleep).
            assert elapsed < 1.0
        finally:
            await _cleanup_workbench(workbench)


@pytest.mark.asyncio
async def test_call_tool_pre_cancelled_token_reports_cancellation() -> None:
    """A token already cancelled before call_tool must report cancellation, not an AttributeError-derived error."""
    call_count = 0

    async def call_tool(name: str, arguments: Any) -> mcp_types.CallToolResult:
        nonlocal call_count
        call_count += 1
        return mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text="done")], isError=False)

    @asynccontextmanager
    async def mock_session_ctx(
        server_params: Any,
        sampling_callback: Any = None,
        elicitation_callback: Any = None,
        list_roots_callback: Any = None,
    ) -> AsyncGenerator[MagicMock, None]:
        mock_session = MagicMock()
        mock_session.initialize = AsyncMock(return_value=_make_initialize_result())
        mock_session.call_tool = call_tool
        yield mock_session

    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", mock_session_ctx):
        workbench = McpWorkbench(server_params=StdioServerParams(command="echo", args=["test"]))
        await workbench.start()
        try:
            token = CancellationToken()
            token.cancel()

            with pytest.raises(asyncio.CancelledError):
                await workbench.call_tool("sleep", {}, cancellation_token=token)

            assert call_count == 0
        finally:
            await _cleanup_workbench(workbench)
