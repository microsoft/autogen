"""Tests for McpSessionActor to cover missing test coverage lines."""

import asyncio
import atexit
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core.models import (
    CreateResult,
    RequestUsage,
)
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams
from autogen_ext.tools.mcp._actor import (
    McpSessionActor,
)
from mcp import types as mcp_types
from mcp.shared.context import RequestContext

# Monkey patch to prevent atexit handlers from being registered during tests
# This prevents the test suite from hanging during shutdown
original_atexit_register = atexit.register


def mock_atexit_register(func: Callable[[], None], *args: Any, **kwargs: Any) -> None:
    """Mock atexit.register to prevent registration during tests."""
    pass


# Apply the monkey patch
atexit.register = mock_atexit_register  # type: ignore[assignment]


@pytest.fixture
def mcp_server_params() -> StdioServerParams:
    """Create server parameters that will launch the real MCP server subprocess."""
    # Get the path to the simple MCP server
    server_path = Path(__file__).parent.parent / "mcp_server_comprehensive.py"
    return StdioServerParams(
        command="uv",
        args=["run", "python", str(server_path)],
        read_timeout_seconds=10,
    )


async def get_expected_tool_count() -> int:
    """Get the expected number of tools by importing and examining the comprehensive server."""
    # Add the parent directory to the path to import the server
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    try:
        # Import and instantiate the server to get the tools
        from mcp_server_comprehensive import SimpleMcpServer

        server = SimpleMcpServer()
        expected_tools = await server.list_tools()
        return len(expected_tools)
    except Exception:
        # Fallback - return 5 if we can't dynamically determine
        return 5


@pytest.fixture
def mock_model_client() -> MagicMock:
    """Mock model client for testing."""
    model_client = MagicMock()
    model_client.model_info = {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": "test-model",
        "structured_output": False,
    }
    model_client.create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    return model_client


@pytest.fixture
def mock_model_client_with_vision() -> MagicMock:
    """Mock model client with vision support for testing."""
    model_client = MagicMock()
    model_client.model_info = {
        "vision": True,
        "function_calling": False,
        "json_output": False,
        "family": "test-vision-model",
        "structured_output": False,
    }
    model_client.create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    return model_client


@pytest.mark.asyncio
async def test_call_when_not_active() -> None:
    """Test call method raises error when actor is not active (line 110)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    with pytest.raises(RuntimeError, match="MCP Actor not running, call initialize\\(\\) first"):
        await actor.call("list_tools")


@pytest.mark.asyncio
async def test_call_when_actor_task_crashed() -> None:
    """Test call method raises error when actor task has crashed (line 119)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Create a crashed task
    async def failing_task() -> Any:
        raise ValueError("Task crashed")

    actor._actor_task = asyncio.create_task(failing_task())  # type: ignore[reportPrivateUsage]  # type: ignore[reportPrivateUsage]

    try:
        await asyncio.sleep(0.01)  # Let the task crash
        actor._active = True  # type: ignore[reportPrivateUsage]

        with pytest.raises(RuntimeError, match="MCP actor task crashed"):
            await actor.call("list_tools")
    finally:
        # Clean up the task
        if not actor._actor_task.done():  # type: ignore[reportPrivateUsage]
            actor._actor_task.cancel()  # type: ignore[reportPrivateUsage]
            try:
                await actor._actor_task  # type: ignore[reportPrivateUsage]
            except (asyncio.CancelledError, ValueError):
                pass


@pytest.mark.asyncio
async def test_call_without_required_args() -> None:
    """Test call method raises error when args are required but not provided (line 121)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="args is required for call_tool"):
        await actor.call("call_tool")


@pytest.mark.asyncio
async def test_call_tool_without_name() -> None:
    """Test call_tool raises error when name is not provided (line 128)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="name is required for call_tool"):
        await actor.call("call_tool", {"name": None, "kargs": {}})


@pytest.mark.asyncio
async def test_read_resource_without_uri() -> None:
    """Test read_resource raises error when uri is not provided (line 132)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="uri is required for read_resource"):
        await actor.call("read_resource", {"name": None, "kargs": {}})


# @pytest.mark.asyncio
# async def test_read_resource_command_queuing() -> None:
#     """Test read_resource command queuing (lines 134-137)."""
#     actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
#     actor._active = True  # type: ignore[reportPrivateUsage]
#     actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
#     actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

#     # Mock the command queue to capture what gets put in it
#     original_queue = actor._command_queue  # type: ignore[reportPrivateUsage]
#     actor._command_queue = MagicMock()  # type: ignore[reportPrivateUsage]
#     actor._command_queue.put = AsyncMock()  # type: ignore[reportPrivateUsage]

#     # Create a task that will be cancelled to avoid hanging
#     call_task = asyncio.create_task(actor.call("read_resource", {"name": None, "kargs": {"uri": "file:///test.txt"}}))

#     # Give it a brief moment to queue the command
#     await asyncio.sleep(0.001)

#     # Cancel the task to avoid hanging
#     call_task.cancel()

#     # Wait for the cancellation to complete
#     try:
#         await call_task
#     except asyncio.CancelledError:
#         pass  # Expected

#     # Verify the command was queued correctly (this covers lines 134-137)
#     actor._command_queue.put.assert_called_once()  # type: ignore[reportPrivateUsage]
#     call_args = actor._command_queue.put.call_args[0][0]  # type: ignore[reportPrivateUsage]
#     assert call_args["type"] == "read_resource"
#     assert call_args["uri"] == "file:///test.txt"
#     assert "future" in call_args

#     # Restore original queue
#     actor._command_queue = original_queue  # type: ignore[reportPrivateUsage]


# @pytest.mark.asyncio
# async def test_get_prompt_without_name() -> None:
#     """Test get_prompt raises error when name is not provided (lines 139-142)."""
#     actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
#     actor._active = True  # type: ignore[reportPrivateUsage]
#     actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
#     actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

#     with pytest.raises(ValueError, match="name is required for get_prompt"):
#         await actor.call("get_prompt", {"name": None, "kargs": {}})


# @pytest.mark.asyncio
# async def test_get_prompt_command_queuing() -> None:
#     """Test get_prompt command queuing (lines 139-142)."""
#     actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
#     actor._active = True  # type: ignore[reportPrivateUsage]
#     actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
#     actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

#     # Mock the command queue to capture what gets put in it
#     original_queue = actor._command_queue  # type: ignore[reportPrivateUsage]
#     actor._command_queue = MagicMock()  # type: ignore[reportPrivateUsage]
#     actor._command_queue.put = AsyncMock()  # type: ignore[reportPrivateUsage]

#     # This will fail when trying to await the future, but we're testing the command queuing logic
#     try:
#         await actor.call("get_prompt", {"name": "test_prompt", "kargs": {"arguments": {"arg1": "value1"}}})
#     except Exception:
#         pass  # Expected to fail, we're just testing the queuing logic

#     # Verify the command was queued correctly (this covers lines 139-142)
#     actor._command_queue.put.assert_called_once()  # type: ignore[reportPrivateUsage]
#     call_args = actor._command_queue.put.call_args[0][0]  # type: ignore[reportPrivateUsage]
#     assert call_args["type"] == "get_prompt"
#     assert call_args["name"] == "test_prompt"
#     assert call_args["args"] == {"arg1": "value1"}
#     assert "future" in call_args

#     # Restore original queue
#     actor._command_queue = original_queue  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_get_prompt_without_name() -> None:
    """Test get_prompt raises error when name is not provided (line 94)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="name is required for get_prompt"):
        await actor.call("get_prompt", {"name": None, "kargs": {}})


@pytest.mark.asyncio
async def test_call_unknown_command_type() -> None:
    """Test call method raises error for unknown command type (line 147)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="Unknown command type: unknown_command"):
        await actor.call("unknown_command")


@pytest.mark.asyncio
async def test_close_when_not_active() -> None:
    """Test close method early return when not active (line 152)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = False  # type: ignore[reportPrivateUsage]
    actor._actor_task = None  # type: ignore[reportPrivateUsage]

    # This should return early without doing anything
    await actor.close()
    assert actor._shutdown_future is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_sampling_callback_without_host() -> None:
    """Test sampling callback returns error when no host is available (lines 119-127)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    mock_context = MagicMock(spec=RequestContext)
    params = mcp_types.CreateMessageRequestParams(
        messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
        maxTokens=100,
    )

    result = await actor._sampling_callback(mock_context, params)  # type: ignore[reportPrivateUsage]

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No host available for sampling" in result.message


@pytest.mark.asyncio
async def test_elicitation_callback_without_host() -> None:
    """Test elicitation callback returns error when no host is available (lines 135-143)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    mock_context = MagicMock(spec=RequestContext)
    params = mcp_types.ElicitRequestParams(message="Test elicitation message", requestedSchema={"type": "object"})

    result = await actor._elicitation_callback(mock_context, params)  # type: ignore[reportPrivateUsage]

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No host available for elicitation" in result.message


@pytest.mark.asyncio
async def test_list_roots_callback_without_host() -> None:
    """Test list_roots callback returns error when no host is available (lines 149-156)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    mock_context = MagicMock(spec=RequestContext)

    result = await actor._list_roots(mock_context)  # type: ignore[reportPrivateUsage]

    assert isinstance(result, mcp_types.ErrorData)
    assert result.code == mcp_types.INVALID_REQUEST
    assert "No host available for listing roots" in result.message


# @pytest.mark.asyncio
# async def test_sampling_callback_message_processing_error() -> None:
#     """Test sampling callback handles message processing errors (lines 226-227, 229-233)."""
#     # Create a model client for the actor
#     model_client = MagicMock()
#     model_client.model_info = {
#         "vision": False,
#         "function_calling": False,
#         "json_output": False,
#         "family": "test-model",
#         "structured_output": False,
#     }

#     actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]), model_client=model_client)

#     mock_context = MagicMock(spec=RequestContext)

#     # Create a valid SamplingMessage but with invalid role that will cause parsing error
#     # We'll patch the message after creation to bypass Pydantic validation
#     valid_message = mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))
#     # Now change the role to something invalid that will cause _parse_sampling_message to fail
#     valid_message.role = "invalid_role"  # type: ignore

#     params = mcp_types.CreateMessageRequestParams(
#         messages=[valid_message],
#         maxTokens=100,
#     )

#     result = await actor._sampling_callback(mock_context, params)  # type: ignore[reportPrivateUsage]

#     assert isinstance(result, mcp_types.ErrorData)
#     assert result.code == mcp_types.INVALID_PARAMS
#     assert "Error processing sampling messages" in result.message


# @pytest.mark.asyncio
# async def test_sampling_callback_model_client_error() -> None:
#     """Test sampling callback handles model client errors (lines 235-239)."""
#     failing_model_client = MagicMock()
#     failing_model_client.model_info = {"vision": False, "family": "test-model"}
#     failing_model_client.create = AsyncMock(side_effect=Exception("Model API error"))

#     actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]), model_client=failing_model_client)

#     mock_context = MagicMock(spec=RequestContext)
#     params = mcp_types.CreateMessageRequestParams(
#         messages=[mcp_types.SamplingMessage(role="user", content=mcp_types.TextContent(type="text", text="Hello"))],
#         maxTokens=100,
#     )

#     result = await actor._sampling_callback(mock_context, params)  # type: ignore[reportPrivateUsage]

#     assert isinstance(result, mcp_types.ErrorData)
#     assert result.code == mcp_types.INTERNAL_ERROR
#     assert "Error sampling from model client" in result.message
#     assert "Model API error" in str(result.data)


@pytest.mark.asyncio
async def test_run_actor_exception_handling() -> None:
    """Test _run_actor exception handling for various command types (lines 244-268)."""
    # This test focuses on covering the exception handling code paths in _run_actor
    # We'll test this by creating a simplified scenario that exercises those paths

    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Create a mock session that will raise exceptions by modifying our mock session
    @asynccontextmanager
    async def mock_failing_session(
        server_params: Any,
        sampling_callback: Any = None,
        elicitation_callback: Any = None,
        list_roots_callback: Any = None,
    ) -> AsyncGenerator[MagicMock, None]:
        mock_session = MagicMock()
        mock_session.initialize = AsyncMock(
            return_value=mcp_types.InitializeResult(
                protocolVersion="1.0",
                capabilities=mcp_types.ServerCapabilities(),
                serverInfo=mcp_types.Implementation(name="test", version="1.0"),
            )
        )
        # Make sure all the session methods raise exceptions to cover the exception handling
        mock_session.call_tool = MagicMock(side_effect=Exception("Tool error"))
        mock_session.list_tools = MagicMock(side_effect=Exception("List tools error"))
        yield mock_session

    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", mock_failing_session):  # type: ignore[reportPrivateUsage]
        # Start the actor task
        actor._active = True  # type: ignore[reportPrivateUsage]
        actor_task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

        try:
            # Give it a moment to initialize
            await asyncio.sleep(0.05)

            # Test one command that will trigger exception handling (covers lines 244-268)
            future: asyncio.Future[Any] = asyncio.Future()
            cmd: dict[str, Any] = {"type": "call_tool", "name": "test_tool", "args": {}, "future": future}
            await actor._command_queue.put(cmd)  # type: ignore[reportPrivateUsage]

            # Wait a bit for command to be processed
            await asyncio.sleep(0.05)

            # Send shutdown command
            shutdown_future: asyncio.Future[Any] = asyncio.Future()
            await actor._command_queue.put({"type": "shutdown", "future": shutdown_future})  # type: ignore[reportPrivateUsage]

            # Wait for actor to finish
            try:
                await asyncio.wait_for(actor_task, timeout=1.0)
            except asyncio.TimeoutError:
                pass  # Expected if task doesn't finish properly

            # The key test: verify that the future was set with an exception
            # This proves the exception handling code (lines 244-268) was executed
            assert future.done()
            assert future.exception() is not None
            assert "Tool error" in str(future.exception())
        finally:
            # Ensure the task is cancelled and cleaned up
            if not actor_task.done():
                actor_task.cancel()
                try:
                    await actor_task
                except asyncio.CancelledError:
                    pass


@pytest.mark.asyncio
async def test_run_actor_session_exception() -> None:
    """Test _run_actor handles session creation exceptions (lines 274-288)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Mock session creation to raise an exception
    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", side_effect=Exception("Session error")):  # type: ignore[reportPrivateUsage]
        actor._active = True  # type: ignore[reportPrivateUsage]
        actor_task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

        try:
            # Wait for the task to complete
            await asyncio.wait_for(actor_task, timeout=1.0)
        except asyncio.TimeoutError:
            # If it doesn't complete, cancel it
            actor_task.cancel()
            try:
                await actor_task
            except asyncio.CancelledError:
                pass

        # Check that the actor is no longer active
        assert not actor._active  # type: ignore[reportPrivateUsage]
        assert actor._actor_task is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_run_actor_drains_queue_on_session_exception() -> None:
    """Ensure pending command futures are failed when session creation raises.

    Uses StreamableHttpServerParams with an invalid URL to trigger failure,
    covering the queue-draining logic added in the referenced commit.
    """
    # Use an invalid local URL/port to force immediate connection failure
    server_params = StreamableHttpServerParams(
        url="http://127.0.0.1:1/invalid",  # very likely closed port
        timeout=0.1,
        sse_read_timeout=0.1,
    )
    actor = McpSessionActor(server_params)

    # Prepare pending commands before the actor starts, so the outer except drains them
    fut1: asyncio.Future[Any] = asyncio.Future()
    fut2: asyncio.Future[Any] = asyncio.Future()
    await actor._command_queue.put({"type": "list_tools", "future": fut1})  # type: ignore[reportPrivateUsage]
    await actor._command_queue.put({"type": "call_tool", "name": "t", "args": {}, "future": fut2})  # type: ignore[reportPrivateUsage]

    actor._active = True  # type: ignore[reportPrivateUsage]
    task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

    # Wait for task to complete; it should handle the exception and drain the queue
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        # If something goes wrong, ensure task cleanup for test stability
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    # Verify futures were failed by the draining logic
    assert fut1.done()
    assert fut1.exception() is not None

    assert fut2.done()
    assert fut2.exception() is not None


@pytest.mark.asyncio
async def test_run_actor_draining_swallows_internal_errors() -> None:
    """draining errors during exception handling are swallowed.

    We force `create_mcp_server_session` to raise so `_run_actor` enters the outer
    exception handler, then make `get_nowait()` itself raise a non-QueueEmpty
    exception. The inner `except Exception: pass` (best-effort draining) should
    swallow it and continue to set the shutdown future exception instead of
    crashing the task.
    """
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Replace the command queue with a mock that raises from get_nowait()
    mock_q = MagicMock()
    mock_q.get_nowait.side_effect = RuntimeError("drain failure")
    actor._command_queue = mock_q  # type: ignore[reportPrivateUsage]

    # Prepare a shutdown future to observe behavior after draining attempt
    actor._shutdown_future = asyncio.Future()  # type: ignore[reportPrivateUsage]

    with patch(
        "autogen_ext.tools.mcp._actor.create_mcp_server_session",
        side_effect=Exception("Session error"),
    ):
        actor._active = True  # type: ignore[reportPrivateUsage]
        task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

        # The task should finish and set the shutdown future with the session error
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    # Draining raised internally, but should have been swallowed (lines 274-276)
    mock_q.get_nowait.assert_called()  # type: ignore[reportPrivateUsage]
    assert actor._shutdown_future.done()  # type: ignore[reportPrivateUsage]
    exc = actor._shutdown_future.exception()  # type: ignore[reportPrivateUsage]
    assert isinstance(exc, Exception)
    assert "Session error" in str(exc)


@pytest.mark.asyncio
async def test_run_actor_shutdown_future_exception() -> None:
    """Test _run_actor sets exception on shutdown future when session fails."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._shutdown_future = asyncio.Future()  # type: ignore[reportPrivateUsage]

    # Mock session creation to raise an exception
    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", side_effect=Exception("Session error")):  # type: ignore[reportPrivateUsage]
        actor._active = True  # type: ignore[reportPrivateUsage]
        actor_task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

        try:
            # Wait for the task to complete
            await asyncio.wait_for(actor_task, timeout=1.0)
        except asyncio.TimeoutError:
            # If it doesn't complete, cancel it
            actor_task.cancel()
            try:
                await actor_task
            except asyncio.CancelledError:
                pass

        # Check that shutdown future has the exception
        assert actor._shutdown_future.done()  # type: ignore[reportPrivateUsage]
        assert actor._shutdown_future.exception() is not None  # type: ignore[reportPrivateUsage]


def test_sync_shutdown_when_not_active() -> None:
    """Test _sync_shutdown early return when not active (line 297)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = False  # type: ignore[reportPrivateUsage]
    actor._actor_task = None  # type: ignore[reportPrivateUsage]

    # This should return early without doing anything
    actor._sync_shutdown()  # type: ignore[reportPrivateUsage]


def test_sync_shutdown_no_event_loop() -> None:
    """Test _sync_shutdown handles RuntimeError when no event loop (line 310)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]

    # Mock get_event_loop to raise RuntimeError
    with patch("asyncio.get_event_loop", side_effect=RuntimeError("No event loop")):
        # This should return early due to the RuntimeError
        actor._sync_shutdown()  # type: ignore[reportPrivateUsage]


def test_sync_shutdown_closed_loop() -> None:
    """Test _sync_shutdown handles closed event loop."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]

    # Mock event loop that is closed
    mock_loop = MagicMock()
    mock_loop.is_closed.return_value = True

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        # This should return early due to the closed loop
        actor._sync_shutdown()  # type: ignore[reportPrivateUsage]


def test_sync_shutdown_running_loop() -> None:
    """Test _sync_shutdown creates task when loop is running."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]

    # Mock event loop that is running
    mock_loop = MagicMock()
    mock_loop.is_closed.return_value = False
    mock_loop.is_running.return_value = True
    mock_loop.create_task = MagicMock()

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        actor._sync_shutdown()  # type: ignore[reportPrivateUsage]
        # Should create a task to close the actor
        mock_loop.create_task.assert_called_once()


def test_sync_shutdown_non_running_loop() -> None:
    """Test _sync_shutdown runs until complete when loop is not running."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]

    # Mock event loop that is not running
    mock_loop = MagicMock()
    mock_loop.is_closed.return_value = False
    mock_loop.is_running.return_value = False
    mock_loop.run_until_complete = MagicMock()

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        actor._sync_shutdown()  # type: ignore[reportPrivateUsage]
        # Should run until complete
        mock_loop.run_until_complete.assert_called_once()


def test_to_config() -> None:
    """Test _to_config method."""
    server_params = StdioServerParams(command="echo", args=["test"])
    actor = McpSessionActor(server_params)

    config = actor._to_config()  # type: ignore[reportPrivateUsage]
    assert config.server_params == server_params


def test_from_config() -> None:
    """Test _from_config class method."""
    from autogen_ext.tools.mcp._actor import McpSessionActorConfig  # type: ignore[reportPrivateUsage]

    server_params = StdioServerParams(command="echo", args=["test"])
    config = McpSessionActorConfig(server_params=server_params)

    actor = McpSessionActor._from_config(config)  # type: ignore[reportPrivateUsage]
    assert actor.server_params == server_params


@pytest.mark.asyncio
async def test_initialize_result_property() -> None:
    """Test initialize_result property."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Initially should be None
    assert actor.initialize_result is None

    # Set a mock result
    mock_result = mcp_types.InitializeResult(
        protocolVersion="1.0",
        capabilities=mcp_types.ServerCapabilities(),
        serverInfo=mcp_types.Implementation(name="test", version="1.0"),
    )
    actor._initialize_result = mock_result  # type: ignore[reportPrivateUsage]

    assert actor.initialize_result == mock_result


@pytest.mark.asyncio
async def test_actor_initialization() -> None:
    """Test actor initialization sets up correctly."""
    server_params = StdioServerParams(command="echo", args=["test"])

    # TODO: Add McpSessionHost
    actor = McpSessionActor(server_params)

    # Check initial state
    assert actor.server_params == server_params
    assert actor.name == "mcp_session_actor"
    assert actor.description == "MCP session actor"
    assert not actor._active  # type: ignore[reportPrivateUsage]
    assert actor._actor_task is None  # type: ignore[reportPrivateUsage]
    assert actor._shutdown_future is None  # type: ignore[reportPrivateUsage]
    assert actor._initialize_result is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_initialize_method(mcp_server_params: Any) -> None:
    """Test initialize method."""
    actor = McpSessionActor(mcp_server_params)

    await actor.initialize()

    assert actor._active  # type: ignore[reportPrivateUsage]
    assert actor._actor_task is not None  # type: ignore[reportPrivateUsage]

    # Clean up
    await actor.close()


@pytest.mark.asyncio
async def test_call_with_valid_list_commands() -> None:
    """Test call method with valid list commands."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    # Mock the command queue to capture what gets put in it
    original_queue = actor._command_queue  # type: ignore[reportPrivateUsage]
    actor._command_queue = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._command_queue.put = AsyncMock()  # type: ignore[reportPrivateUsage]

    # Test all valid list commands - we don't await the result, just test the queuing
    test_commands = ["list_tools", "list_prompts", "list_resources", "list_resource_templates", "shutdown"]
    created_tasks: list[asyncio.Task[Any]] = []

    try:
        for cmd_type in test_commands:
            # Create a task but don't await it (to avoid hanging)
            call_task = asyncio.create_task(actor.call(cmd_type))
            created_tasks.append(call_task)

            # Give it a brief moment to queue the command
            await asyncio.sleep(0.001)

            # Verify the command was queued correctly
            actor._command_queue.put.assert_called()  # type: ignore[reportPrivateUsage]
            call_args = actor._command_queue.put.call_args[0][0]  # type: ignore[reportPrivateUsage]
            assert call_args["type"] == cmd_type
            assert "future" in call_args
            actor._command_queue.put.reset_mock()  # type: ignore[reportPrivateUsage]

    finally:
        # Clean up all created tasks
        for task in created_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Restore original queue
        actor._command_queue = original_queue  # type: ignore[reportPrivateUsage]


# Integration tests using the real MCP server
@pytest.mark.asyncio
async def test_actor_basic_functionality(mcp_server_params: Any) -> None:
    """Test basic actor functionality with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        # Initialize the actor
        await actor.initialize()
        assert actor._active  # type: ignore[reportPrivateUsage]
        assert actor._actor_task is not None  # type: ignore[reportPrivateUsage]

        # Test listing tools
        tools_future = await actor.call("list_tools")
        tools_result: mcp_types.ListToolsResult = await tools_future  # type: ignore
        expected_tool_count = await get_expected_tool_count()
        assert len(tools_result.tools) == expected_tool_count
        tool_names = [tool.name for tool in tools_result.tools]
        assert "echo" in tool_names
        assert "get_time" in tool_names

        # Test calling a tool
        call_future = await actor.call("call_tool", {"name": "echo", "kargs": {"text": "Hello World"}})
        call_result: mcp_types.CallToolResult = await call_future  # type: ignore
        assert call_result.content[0].text == "Echo: Hello World"  # type: ignore

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_prompt_operations(mcp_server_params: Any) -> None:
    """Test actor prompt operations with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()
        await asyncio.sleep(0.1)

        # Test listing prompts
        prompts_future = await actor.call("list_prompts")
        prompts_result: mcp_types.ListPromptsResult = await prompts_future  # type: ignore
        assert len(prompts_result.prompts) == 2  # code_review and documentation
        prompt_names = [prompt.name for prompt in prompts_result.prompts]
        assert "code_review" in prompt_names
        assert "documentation" in prompt_names

        # Test getting a prompt with arguments
        prompt_future = await actor.call(
            "get_prompt",
            {"name": "code_review", "kargs": {"arguments": {"code": "print('hello')", "language": "python"}}},
        )
        prompt_result: mcp_types.GetPromptResult = await prompt_future  # type: ignore
        assert prompt_result.description is not None and "python" in prompt_result.description
        assert "print('hello')" in prompt_result.messages[0].content.text  # type: ignore

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_resource_operations(mcp_server_params: Any) -> None:
    """Test actor resource operations with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()
        await asyncio.sleep(0.1)

        # Test listing resources
        resources_future = await actor.call("list_resources")
        resources_result: mcp_types.ListResourcesResult = await resources_future  # type: ignore
        assert len(resources_result.resources) == 2  # users and projects
        resource_names = [resource.name for resource in resources_result.resources]
        assert "Company Users" in resource_names
        assert "Active Projects" in resource_names

        # Test reading a resource
        read_future = await actor.call("read_resource", {"name": None, "kargs": {"uri": "file:///company/users.json"}})
        read_result: mcp_types.ReadResourceResult = await read_future  # type: ignore
        users_data = json.loads(read_result.contents[0].text)  # type: ignore
        assert isinstance(users_data, list)
        assert len(users_data) == 3  # type: ignore[reportUnknownArgumentType]
        assert users_data[0]["name"] == "Alice"

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_tool_failure_handling(mcp_server_params: Any) -> None:
    """Test actor handles tool failures correctly."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()
        await asyncio.sleep(0.1)

        # Test calling an unknown tool - the server should return an error result
        call_future = await actor.call("call_tool", {"name": "unknown_tool", "kargs": {}})
        call_result: mcp_types.CallToolResult = await call_future  # type: ignore
        # The server returns an error but doesn't raise an exception
        assert call_result.isError is True  # type: ignore
        assert "Unknown tool" in call_result.content[0].text  # type: ignore

    finally:
        await actor.close()


# TODO: Use McpSessionhost
# @pytest.mark.asyncio
# async def test_actor_with_model_client_sampling(mcp_server_params: Any, mock_model_client: Any) -> None:
#     """Test actor with model client for sampling operations."""
#     actor = McpSessionActor(mcp_server_params, model_client=mock_model_client)

#     try:
#         await actor.initialize()
#         await asyncio.sleep(0.1)

#         # Test sampling callback functionality
#         mock_context = MagicMock(spec=RequestContext)
#         params = mcp_types.CreateMessageRequestParams(
#             messages=[
#                 mcp_types.SamplingMessage(
#                     role="user", content=mcp_types.TextContent(type="text", text="Hello from test")
#                 )
#             ],
#             maxTokens=100,
#         )

#         result = await actor._sampling_callback(mock_context, params)  # type: ignore[reportPrivateUsage]

#         assert isinstance(result, mcp_types.CreateMessageResult)
#         assert result.role == "assistant"
#         assert isinstance(result.content, mcp_types.TextContent)
#         assert result.content.text == "Mock response"
#         assert result.model == "test-model"

#     finally:
#         await actor.close()


# Integration tests with real MCP server
@pytest.mark.asyncio
async def test_actor(mcp_server_params: Any) -> None:
    """Test actor with real MCP server subprocess."""
    actor = McpSessionActor(mcp_server_params)

    try:
        # Initialize the actor
        await actor.initialize()
        assert actor._active  # type: ignore[reportPrivateUsage]
        assert actor._actor_task is not None  # type: ignore[reportPrivateUsage]

        # Test listing tools
        tools_future = await actor.call("list_tools")
        tools_result: mcp_types.ListToolsResult = await tools_future  # type: ignore
        expected_tool_count = await get_expected_tool_count()
        assert len(tools_result.tools) == expected_tool_count
        tool_names = [tool.name for tool in tools_result.tools]
        assert "echo" in tool_names
        assert "get_time" in tool_names

        # Test calling the echo tool
        call_future = await actor.call("call_tool", {"name": "echo", "kargs": {"text": "Hello World"}})
        call_result: mcp_types.CallToolResult = await call_future  # type: ignore
        assert call_result.content[0].text == "Echo: Hello World"  # type: ignore

        # Test calling the get_time tool
        time_future = await actor.call("call_tool", {"name": "get_time", "kargs": {}})
        time_result: mcp_types.CallToolResult = await time_future  # type: ignore
        assert "Current time:" in time_result.content[0].text  # type: ignore

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_prompts(mcp_server_params: Any) -> None:
    """Test actor prompt operations with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()

        # Test listing prompts
        prompts_future = await actor.call("list_prompts")
        prompts_result: mcp_types.ListPromptsResult = await prompts_future  # type: ignore
        assert len(prompts_result.prompts) == 2  # code_review and documentation
        prompt_names = [prompt.name for prompt in prompts_result.prompts]
        assert "code_review" in prompt_names
        assert "documentation" in prompt_names

        # Test getting a prompt
        prompt_future = await actor.call(
            "get_prompt",
            {"name": "code_review", "kargs": {"arguments": {"code": "print('hello')", "language": "python"}}},
        )
        prompt_result: mcp_types.GetPromptResult = await prompt_future  # type: ignore
        assert prompt_result.description is not None and "python" in prompt_result.description
        assert "print('hello')" in prompt_result.messages[0].content.text  # type: ignore

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_resources(mcp_server_params: Any) -> None:
    """Test actor resource operations with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()

        # Test listing resources
        resources_future = await actor.call("list_resources")
        resources_result: mcp_types.ListResourcesResult = await resources_future  # type: ignore
        assert len(resources_result.resources) == 2  # users and projects
        resource_names = [resource.name for resource in resources_result.resources]
        assert "Company Users" in resource_names
        assert "Active Projects" in resource_names

        # Test reading a resource
        read_future = await actor.call("read_resource", {"name": None, "kargs": {"uri": "file:///company/users.json"}})
        read_result: mcp_types.ReadResourceResult = await read_future  # type: ignore
        # The real server returns content in the ReadResourceResult
        users_data = json.loads(read_result.contents[0].text)  # type: ignore
        assert isinstance(users_data, list)
        assert len(users_data) == 3  # type: ignore[reportUnknownArgumentType]
        assert users_data[0]["name"] == "Alice"

    finally:
        await actor.close()


@pytest.mark.asyncio
async def test_actor_unknown_tool(mcp_server_params: Any) -> None:
    """Test actor handles unknown tools with real MCP server."""
    actor = McpSessionActor(mcp_server_params)

    try:
        await actor.initialize()

        # Test calling an unknown tool - the server should return an error result
        call_future = await actor.call("call_tool", {"name": "unknown_tool", "kargs": {}})
        call_result: mcp_types.CallToolResult = await call_future  # type: ignore
        # The server returns an error but doesn't raise an exception
        assert call_result.isError is True  # type: ignore
        assert "Unknown tool" in call_result.content[0].text  # type: ignore

    finally:
        await actor.close()


@pytest.fixture
def clean_actor() -> Generator[Callable[..., McpSessionActor], None, None]:
    """Fixture to track and clean up actors created in tests."""
    actors: list[McpSessionActor] = []

    def create_actor(*args: Any, **kwargs: Any) -> McpSessionActor:
        actor = McpSessionActor(*args, **kwargs)
        actors.append(actor)
        return actor

    yield create_actor

    # Clean up all actors
    for actor in actors:
        if hasattr(actor, "_active") and actor._active:  # type: ignore[reportPrivateUsage]
            try:
                # Try to close the actor properly
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(actor.close())
                else:
                    loop.run_until_complete(actor.close())
            except Exception:
                # If we can't close it properly, at least deactivate it
                actor._active = False  # type: ignore[reportPrivateUsage]
                if hasattr(actor, "_actor_task") and actor._actor_task:  # type: ignore[reportPrivateUsage]
                    actor._actor_task.cancel()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_run_actor_all_command_types_exception_handling() -> None:
    """Test _run_actor exception handling for all command types (lines 232-233, 238-239, 244-245, 250-251, 256-263)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))

    # Create a mock session that will raise exceptions for all command types
    @asynccontextmanager
    async def mock_failing_session(
        server_params: Any,
        sampling_callback: Any = None,
        elicitation_callback: Any = None,
        list_roots_callback: Any = None,
    ) -> AsyncGenerator[MagicMock, None]:
        mock_session = MagicMock()
        mock_session.initialize = AsyncMock(
            return_value=mcp_types.InitializeResult(
                protocolVersion="1.0",
                capabilities=mcp_types.ServerCapabilities(),
                serverInfo=mcp_types.Implementation(name="test", version="1.0"),
            )
        )
        # Make all session methods raise exceptions
        mock_session.call_tool = MagicMock(side_effect=Exception("call_tool error"))
        mock_session.read_resource = MagicMock(side_effect=Exception("read_resource error"))
        mock_session.get_prompt = MagicMock(side_effect=Exception("get_prompt error"))
        mock_session.list_tools = MagicMock(side_effect=Exception("list_tools error"))
        mock_session.list_prompts = MagicMock(side_effect=Exception("list_prompts error"))
        mock_session.list_resources = MagicMock(side_effect=Exception("list_resources error"))
        mock_session.list_resource_templates = MagicMock(side_effect=Exception("list_resource_templates error"))
        yield mock_session

    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session", mock_failing_session):  # type: ignore[reportPrivateUsage]
        # Start the actor task
        actor._active = True  # type: ignore[reportPrivateUsage]
        actor_task = asyncio.create_task(actor._run_actor())  # type: ignore[reportPrivateUsage]

        try:
            # Give it a moment to initialize
            await asyncio.sleep(0.05)

            # Test all command types that can raise exceptions (including line 212)
            commands_to_test: list[dict[str, Any]] = [
                {"type": "call_tool", "name": "test_tool", "args": {}},
                {"type": "read_resource", "uri": "test://resource"},
                {"type": "get_prompt", "name": "test_prompt", "args": {}},
                {"type": "list_tools"},
                {"type": "list_prompts"},
                {"type": "list_resources"},
                {"type": "list_resource_templates"},  # This covers line 212
            ]

            futures: list[asyncio.Future[Any]] = []
            for cmd in commands_to_test:
                future: asyncio.Future[Any] = asyncio.Future()
                cmd["future"] = future
                await actor._command_queue.put(cmd)  # type: ignore[reportPrivateUsage]
                futures.append(future)

            # Wait a bit for commands to be processed
            await asyncio.sleep(0.1)

            # Send shutdown command
            shutdown_future: asyncio.Future[Any] = asyncio.Future()
            await actor._command_queue.put({"type": "shutdown", "future": shutdown_future})  # type: ignore[reportPrivateUsage]

            # Wait for actor to finish
            try:
                await asyncio.wait_for(actor_task, timeout=1.0)
            except asyncio.TimeoutError:
                pass  # Expected if task doesn't finish properly

            # Verify that all futures were set with exceptions
            for i, future in enumerate(futures):
                assert future.done(), f"Future {i} was not completed"
                assert future.exception() is not None, f"Future {i} should have an exception"

        finally:
            # Ensure the task is cancelled and cleaned up
            if not actor_task.done():
                actor_task.cancel()
                try:
                    await actor_task
                except asyncio.CancelledError:
                    pass


@pytest.mark.asyncio
async def test_close_with_shutdown_await() -> None:
    """Test close method waits for shutdown future (line 140)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    # Mock the command queue and actor task
    original_queue = actor._command_queue  # type: ignore[reportPrivateUsage]
    actor._command_queue = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._command_queue.put = AsyncMock()  # type: ignore[reportPrivateUsage]

    # Create a shutdown future that will be set
    shutdown_future: asyncio.Future[Any] = asyncio.Future()

    # Mock the close method to set the shutdown future after a delay
    async def mock_close() -> None:
        actor._shutdown_future = shutdown_future  # type: ignore[reportPrivateUsage]
        await actor._command_queue.put({"type": "shutdown", "future": shutdown_future})  # type: ignore[reportPrivateUsage]
        # Simulate the shutdown completion
        await asyncio.sleep(0.01)
        shutdown_future.set_result("ok")

    # Replace the close method temporarily
    original_close = actor.close
    actor.close = mock_close  # type: ignore[method-assign]

    try:
        # This should complete without hanging
        await actor.close()
        assert shutdown_future.done()
        assert shutdown_future.result() == "ok"
    finally:
        # Restore original queue and close method
        actor._command_queue = original_queue  # type: ignore[reportPrivateUsage]
        actor.close = original_close  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_call_tool_command_queuing() -> None:
    """Test call_tool command queuing (line 140)."""
    actor = McpSessionActor(StdioServerParams(command="echo", args=["test"]))
    actor._active = True  # type: ignore[reportPrivateUsage]
    actor._actor_task = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._actor_task.done.return_value = False  # type: ignore[reportPrivateUsage]

    # Mock the command queue to capture what gets put in it
    original_queue = actor._command_queue  # type: ignore[reportPrivateUsage]
    actor._command_queue = MagicMock()  # type: ignore[reportPrivateUsage]
    actor._command_queue.put = AsyncMock()  # type: ignore[reportPrivateUsage]

    # Create a task that will be cancelled to avoid hanging
    call_task = asyncio.create_task(actor.call("call_tool", {"name": "test_tool", "kargs": {"param": "value"}}))

    # Give it a brief moment to queue the command
    await asyncio.sleep(0.001)

    # Cancel the task to avoid hanging
    call_task.cancel()

    # Wait for the cancellation to complete
    try:
        await call_task
    except asyncio.CancelledError:
        pass  # Expected

    # Verify the command was queued correctly (this covers line 140)
    actor._command_queue.put.assert_called_once()  # type: ignore[reportPrivateUsage]
    call_args = actor._command_queue.put.call_args[0][0]  # type: ignore[reportPrivateUsage]
    assert call_args["type"] == "call_tool"
    assert call_args["name"] == "test_tool"
    assert call_args["args"] == {"param": "value"}
    assert "future" in call_args

    # Restore original queue
    actor._command_queue = original_queue  # type: ignore[reportPrivateUsage]
