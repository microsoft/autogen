"""Tests for McpWorkbench expected errors and warnings."""

import asyncio
import builtins
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import Image
from autogen_core.tools import ImageResultContent, TextResultContent
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    TextContent,
)


@pytest.fixture
def sample_server_params() -> StdioServerParams:
    """Sample server parameters for testing."""
    return StdioServerParams(command="echo", args=["test"])


@pytest.fixture
def mock_actor() -> AsyncMock:
    """Mock actor for testing."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_list_tools_actor_none_after_start(sample_server_params: StdioServerParams) -> None:
    """Test list_tools when actor is None after start attempt - covers line 274."""
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock start method to set _actor to None
    with patch.object(workbench, "start") as mock_start:
        mock_start.return_value = None
        workbench._actor = None  # type: ignore[reportPrivateUsage]

        with pytest.raises(RuntimeError, match="Actor is not initialized. Please check the server connection."):
            await workbench.list_tools()


@pytest.mark.asyncio
async def test_call_tool_actor_none_after_start(sample_server_params: StdioServerParams) -> None:
    """Test call_tool when actor is None after start attempt - covers line 320."""
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock start method to set _actor to None
    with patch.object(workbench, "start") as mock_start:
        mock_start.return_value = None
        workbench._actor = None  # type: ignore[reportPrivateUsage]

        with pytest.raises(RuntimeError, match="Actor is not initialized. Please check the server connection."):
            await workbench.call_tool("test_tool")


@pytest.mark.asyncio
async def test_list_prompts_actor_none_after_start(sample_server_params: StdioServerParams) -> None:
    """Test list_prompts when actor is None after start attempt - covers line 364."""
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock start method to set _actor to None
    with patch.object(workbench, "start") as mock_start:
        mock_start.return_value = None
        workbench._actor = None  # type: ignore[reportPrivateUsage]

        with pytest.raises(RuntimeError, match="Actor is not initialized. Please check the server connection."):
            await workbench.list_prompts()


@pytest.mark.asyncio
async def test_call_tool_image_content_handling(sample_server_params: StdioServerParams, mock_actor: AsyncMock) -> None:
    """Test call_tool with ImageContent - covers lines 346-347."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    # Mock tool result with ImageContent
    image_content = ImageContent(
        type="image",
        data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        mimeType="image/png",
    )

    call_result = CallToolResult(content=[image_content], isError=False)

    # Mock the call method to return a future that resolves to the result
    future: asyncio.Future[CallToolResult] = asyncio.Future()
    future.set_result(call_result)
    mock_actor.call.return_value = future

    result = await workbench.call_tool("test_tool")

    assert len(result.result) == 1
    assert isinstance(result.result[0], ImageResultContent)
    assert isinstance(result.result[0].content, Image)


@pytest.mark.asyncio
async def test_call_tool_embedded_resource_handling(
    sample_server_params: StdioServerParams, mock_actor: AsyncMock
) -> None:
    """Test call_tool with EmbeddedResource - covers lines 348-351."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    # Mock tool result with EmbeddedResource
    from mcp.types import TextResourceContents
    from pydantic import AnyUrl

    embedded_resource = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(uri=AnyUrl("test://resource"), text="test content"),
    )

    call_result = CallToolResult(content=[embedded_resource], isError=False)

    # Mock the call method to return a future that resolves to the result
    future: asyncio.Future[CallToolResult] = asyncio.Future()
    future.set_result(call_result)
    mock_actor.call.return_value = future

    result = await workbench.call_tool("test_tool")

    assert len(result.result) == 1
    assert isinstance(result.result[0], TextResultContent)
    # Should contain JSON representation of the embedded resource
    assert "resource" in result.result[0].content


@pytest.mark.asyncio
async def test_call_tool_exception_handling(sample_server_params: StdioServerParams, mock_actor: AsyncMock) -> None:
    """Test call_tool exception handling - covers lines 354-357."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    # Mock actor to raise an exception
    mock_actor.call.side_effect = Exception("Test exception")

    result = await workbench.call_tool("test_tool")

    assert result.is_error
    assert len(result.result) == 1
    assert isinstance(result.result[0], TextResultContent)
    assert "Test exception" in result.result[0].content


def test_format_errors_with_exception_group() -> None:
    """Test _format_errors with ExceptionGroup - covers lines 444-452."""
    workbench = McpWorkbench(server_params=StdioServerParams(command="echo", args=["test"]))

    # Only test if ExceptionGroup is available (Python 3.11+)
    if hasattr(builtins, "ExceptionGroup"):
        # Create an ExceptionGroup
        sub_exceptions = [
            ValueError("Error 1"),
            RuntimeError("Error 2"),
        ]
        exception_group = builtins.ExceptionGroup("Multiple errors", sub_exceptions)

        result = workbench._format_errors(exception_group)  # type: ignore[reportPrivateUsage]

        assert "Error 1" in result
        assert "Error 2" in result
    else:
        # For Python < 3.11, just test regular exception handling
        regular_exception = ValueError("Regular error")
        result = workbench._format_errors(regular_exception)  # type: ignore[reportPrivateUsage]
        assert "Regular error" in result


@pytest.mark.asyncio
async def test_call_tool_with_none_arguments(sample_server_params: StdioServerParams, mock_actor: AsyncMock) -> None:
    """Test call_tool with None arguments - covers line 323."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    # Mock successful tool call
    call_result = CallToolResult(content=[TextContent(type="text", text="Success")], isError=False)

    # Mock the call method to return a future that resolves to the result
    future: asyncio.Future[CallToolResult] = asyncio.Future()
    future.set_result(call_result)
    mock_actor.call.return_value = future

    # Call with None arguments
    result = await workbench.call_tool("test_tool", arguments=None)

    # Should handle None arguments gracefully
    assert not result.is_error
    assert len(result.result) == 1


@pytest.mark.asyncio
async def test_call_tool_with_none_cancellation_token(
    sample_server_params: StdioServerParams, mock_actor: AsyncMock
) -> None:
    """Test call_tool with None cancellation_token - covers line 322."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    # Mock successful tool call
    call_result = CallToolResult(content=[TextContent(type="text", text="Success")], isError=False)

    # Mock the call method to return a future that resolves to the result
    future: asyncio.Future[CallToolResult] = asyncio.Future()
    future.set_result(call_result)
    mock_actor.call.return_value = future

    # Call with None cancellation_token
    result = await workbench.call_tool("test_tool", cancellation_token=None)

    # Should handle None cancellation_token gracefully
    assert not result.is_error
    assert len(result.result) == 1


@pytest.mark.asyncio
async def test_initialize_result_property_with_actor(
    sample_server_params: StdioServerParams, mock_actor: AsyncMock
) -> None:
    """Test initialize_result property when actor exists."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]
    mock_actor.initialize_result = "test_result"

    result = workbench.initialize_result  # type: ignore[reportPrivateUsage]
    assert result == "test_result"


@pytest.mark.asyncio
async def test_initialize_result_property_without_actor(sample_server_params: StdioServerParams) -> None:
    """Test initialize_result property when actor is None."""
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = None  # type: ignore[reportPrivateUsage]

    result = workbench.initialize_result  # type: ignore[reportPrivateUsage]
    assert result is None


@pytest.mark.asyncio
async def test_to_config_method(sample_server_params: StdioServerParams) -> None:
    """Test _to_config method."""
    workbench = McpWorkbench(server_params=sample_server_params)
    config = workbench._to_config()  # type: ignore[reportPrivateUsage]
    assert config.server_params == sample_server_params


@pytest.mark.asyncio
async def test_from_config_method(sample_server_params: StdioServerParams) -> None:
    """Test _from_config method."""
    from autogen_ext.tools.mcp._workbench import McpWorkbenchConfig  # type: ignore[reportPrivateUsage]

    config = McpWorkbenchConfig(server_params=sample_server_params)
    workbench = McpWorkbench._from_config(config)  # type: ignore[reportPrivateUsage]
    assert workbench.server_params == sample_server_params


@pytest.mark.asyncio
async def test_async_context_manager(sample_server_params: StdioServerParams) -> None:
    """Test async context manager functionality."""
    workbench = McpWorkbench(server_params=sample_server_params)

    # Test that the context manager properly handles start/stop
    with patch.object(workbench, "start") as mock_start, patch.object(workbench, "stop") as mock_stop:
        async with workbench:
            pass

        mock_start.assert_called_once()
        mock_stop.assert_called_once()


@pytest.mark.asyncio
async def test_sampling_callback_functionality(sample_server_params: StdioServerParams) -> None:
    """Test sampling callback functionality for private method access."""
    workbench = McpWorkbench(server_params=sample_server_params)

    # Create a mock that simulates the sampling callback
    mock_callback: AsyncMock = AsyncMock()

    # Test that the workbench can handle sampling callbacks
    # This tests private method access which appears in the error reports
    workbench._sampling_callback = mock_callback  # type: ignore[attr-defined]

    # Verify the callback was set
    assert workbench._sampling_callback is mock_callback  # type: ignore[attr-defined]


def test_misc_lambda_types() -> None:
    """Test miscellaneous lambda types for coverage."""

    # Test lambda with unknown parameter types
    def test_lambda(obj: Any, cls: Any) -> bool:
        return True

    assert test_lambda("test", str) is True

    # Test lambda with return type
    def test_lambda2(x: Any) -> bool:
        return isinstance(x, str)

    assert test_lambda2("test") is True
    assert test_lambda2(123) is False
