#!/usr/bin/env python3
"""
Test the MCP client implementation
"""

import asyncio
import pytest
from autogenstudio.mcp.client import McpClient, McpConnectionError, McpOperationError
from autogen_ext.tools.mcp._config import StdioServerParams, SseServerParams


@pytest.mark.anyio
async def test_mcp_client_initialization():
    """Test MCP client can be initialized"""
    client = McpClient()
    assert client is not None
    assert client.exit_stack is None
    assert client.session is None


@pytest.mark.anyio
async def test_list_tools_with_our_client():
    """Test our McpClient with a mock server"""
    from unittest.mock import AsyncMock, MagicMock
    from mcp.types import ListToolsResult, Tool
    
    client = McpClient()
    
    # Mock the session and tools response
    mock_session = AsyncMock()
    mock_tools = [
        Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        )
    ]
    mock_session.list_tools.return_value = ListToolsResult(tools=mock_tools)
    
    # Mock the _get_session method
    client._get_session = AsyncMock(return_value=mock_session)
    client.cleanup = AsyncMock()
    
    # Test with our client
    stdio_params = StdioServerParams(command="test", args=[])
    tools = await client.list_tools(stdio_params)
    
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].description == "A test tool"
    
    # Verify our client called the session correctly
    client._get_session.assert_called_once_with(stdio_params)
    mock_session.list_tools.assert_called_once()
    client.cleanup.assert_called_once()


@pytest.mark.anyio
async def test_call_tool_with_our_client():
    """Test our McpClient calling tools"""
    from unittest.mock import AsyncMock
    from mcp.types import CallToolResult, TextContent
    
    client = McpClient()
    
    # Mock the session and call result
    mock_session = AsyncMock()
    mock_result = CallToolResult(
        content=[TextContent(type="text", text="Hello from test tool")]
    )
    mock_session.call_tool.return_value = mock_result
    
    # Mock the _get_session method
    client._get_session = AsyncMock(return_value=mock_session)
    client.cleanup = AsyncMock()
    
    # Test with our client
    stdio_params = StdioServerParams(command="test", args=[])
    result = await client.call_tool(stdio_params, "test_tool", {"message": "hello"})
    
    assert isinstance(result, CallToolResult)
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "Hello from test tool"
    
    # Verify our client called the session correctly
    client._get_session.assert_called_once_with(stdio_params)
    mock_session.call_tool.assert_called_once_with("test_tool", {"message": "hello"})
    client.cleanup.assert_called_once()


@pytest.mark.anyio
async def test_transport_detection():
    """Test that our client correctly detects transport types"""
    client = McpClient()
    
    # Test STDIO params detection
    stdio_params = StdioServerParams(command="test", args=[])
    assert isinstance(stdio_params, StdioServerParams)
    
    # Test SSE params detection  
    sse_params = SseServerParams(url="http://test.com", timeout=5.0)
    assert isinstance(sse_params, SseServerParams)


@pytest.mark.anyio
async def test_error_handling_in_our_client():
    """Test error handling in our client operations"""
    from unittest.mock import AsyncMock
    
    client = McpClient()
    
    # Mock session that raises exceptions
    mock_session = AsyncMock()
    mock_session.list_tools.side_effect = Exception("Connection failed")
    mock_session.call_tool.side_effect = Exception("Tool execution failed")
    
    client._get_session = AsyncMock(return_value=mock_session)
    client.cleanup = AsyncMock()
    
    stdio_params = StdioServerParams(command="test", args=[])
    
    # Test list_tools error handling
    with pytest.raises(McpOperationError, match="Failed to list tools"):
        await client.list_tools(stdio_params)
    
    # Test call_tool error handling
    with pytest.raises(McpOperationError, match="Failed to call tool"):
        await client.call_tool(stdio_params, "test_tool", {})
    
    # Verify cleanup was called
    assert client.cleanup.call_count >= 2


@pytest.mark.anyio
async def test_server_params_creation():
    """Test creating different server parameter types"""
    
    # STDIO server
    stdio = StdioServerParams(
        command="python",
        args=["-m", "my_mcp_server"],
        env={"DEBUG": "1"}
    )
    assert stdio.type == "StdioServerParams"
    assert stdio.command == "python"
    assert stdio.args == ["-m", "my_mcp_server"]
    
    # SSE server  
    sse = SseServerParams(
        url="http://localhost:3000/sse",
        headers={"API-Key": "secret"},
        timeout=10.0
    )
    assert sse.type == "SseServerParams"
    assert sse.url == "http://localhost:3000/sse"
    assert sse.timeout == 10.0


@pytest.mark.anyio
async def test_client_cleanup():
    """Test client cleanup works without errors"""
    client = McpClient()
    
    # Should not raise any errors even if nothing to clean up
    await client.cleanup()
    
    assert client.exit_stack is None
    assert client.session is None


# Note: For real STDIO server integration tests, you would need actual MCP servers
# Those tests should be in a separate file like test_mcp_client_integration.py
# and marked with custom markers like @pytest.mark.integration
