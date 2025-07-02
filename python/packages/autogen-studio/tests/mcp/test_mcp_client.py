#!/usr/bin/env python3
"""Test the MCP client implementation"""

import asyncio
import pytest
from autogenstudio.mcp.client import McpClient, McpConnectionError, McpOperationError
from autogen_ext.tools.mcp._config import StdioServerParams, SseServerParams


@pytest.mark.anyio
async def test_mcp_client_initialization():
    """Test MCP client can be initialized"""
    client = McpClient()
    assert client is not None


@pytest.mark.anyio
async def test_list_tools_with_mocked_session():
    """Test our McpClient with a mock session"""
    from unittest.mock import AsyncMock, patch
    from mcp.types import ListToolsResult, Tool, InitializeResult, Implementation, ServerCapabilities
    
    client = McpClient()
    
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
    
    mock_session = AsyncMock()
    mock_session.list_tools.return_value = ListToolsResult(tools=mock_tools)
    mock_session.initialize.return_value = InitializeResult(
        protocolVersion="2024-11-05",
        capabilities=ServerCapabilities(),
        serverInfo=Implementation(name="test-server", version="1.0.0")
    )
    
    async def mock_execute(server_params, operation):
        return await operation(mock_session, mock_session.initialize.return_value)
    
    with patch.object(client, '_execute_with_session', side_effect=mock_execute):
        stdio_params = StdioServerParams(command="test", args=[])
        tools = await client.list_tools(stdio_params)
    
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].description == "A test tool"
    
    mock_session.list_tools.assert_called_once()


@pytest.mark.anyio
async def test_call_tool_with_mocked_session():
    """Test our McpClient calling tools"""
    from unittest.mock import AsyncMock, patch
    from mcp.types import CallToolResult, TextContent, InitializeResult, Implementation, ServerCapabilities
    
    client = McpClient()
    
    mock_session = AsyncMock()
    mock_result = CallToolResult(
        content=[TextContent(type="text", text="Hello from test tool")]
    )
    mock_session.call_tool.return_value = mock_result
    mock_session.initialize.return_value = InitializeResult(
        protocolVersion="2024-11-05",
        capabilities=ServerCapabilities(),
        serverInfo=Implementation(name="test-server", version="1.0.0")
    )
    
    async def mock_execute(server_params, operation):
        return await operation(mock_session, mock_session.initialize.return_value)
    
    with patch.object(client, '_execute_with_session', side_effect=mock_execute):
        stdio_params = StdioServerParams(command="test", args=[])
        result = await client.call_tool(stdio_params, "test_tool", {"message": "hello"})
    
    assert isinstance(result, CallToolResult)
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "Hello from test tool"
    
    mock_session.call_tool.assert_called_once_with("test_tool", {"message": "hello"})


@pytest.mark.anyio
async def test_transport_detection():
    """Test that our client correctly detects transport types"""
    client = McpClient()
    
    stdio_params = StdioServerParams(command="test", args=[])
    assert isinstance(stdio_params, StdioServerParams)
    
    sse_params = SseServerParams(url="http://test.com", timeout=5.0)
    assert isinstance(sse_params, SseServerParams)


@pytest.mark.anyio
async def test_error_handling_in_our_client():
    """Test error handling in our client operations"""
    from unittest.mock import AsyncMock, patch
    
    client = McpClient()
    
    async def mock_execute_error(server_params, operation):
        raise Exception("Connection failed")
    
    stdio_params = StdioServerParams(command="test", args=[])
    
    with patch.object(client, '_execute_with_session', side_effect=mock_execute_error):
        with pytest.raises(McpOperationError, match="Failed to list tools"):
            await client.list_tools(stdio_params)
    
    with patch.object(client, '_execute_with_session', side_effect=mock_execute_error):
        with pytest.raises(McpOperationError, match="Failed to call tool"):
            await client.call_tool(stdio_params, "test_tool", {})


@pytest.mark.anyio
async def test_server_params_creation():
    """Test creating different server parameter types"""
    
    stdio = StdioServerParams(
        command="python",
        args=["-m", "my_mcp_server"],
        env={"DEBUG": "1"}
    )
    assert stdio.type == "StdioServerParams"
    assert stdio.command == "python"
    assert stdio.args == ["-m", "my_mcp_server"]
    
    sse = SseServerParams(
        url="http://localhost:3000/sse",
        headers={"API-Key": "secret"},
        timeout=10.0
    )
    assert sse.type == "SseServerParams"
    assert sse.url == "http://localhost:3000/sse"
    assert sse.timeout == 10.0


@pytest.mark.anyio
async def test_client_context_manager():
    """Test client context manager works without errors"""
    client = McpClient()
    
    async with client:
        assert client is not None


@pytest.mark.anyio
async def test_get_capabilities():
    """Test getting server capabilities"""
    from unittest.mock import AsyncMock, patch
    from mcp.types import ServerCapabilities, ToolsCapability, ResourcesCapability, PromptsCapability, InitializeResult, Implementation
    
    client = McpClient()
    
    mock_capabilities = ServerCapabilities(
        tools=ToolsCapability(listChanged=False),
        resources=ResourcesCapability(subscribe=False, listChanged=False),
        prompts=PromptsCapability(listChanged=False)
    )
    
    mock_initialize_result = InitializeResult(
        protocolVersion="2025-03-26",
        capabilities=mock_capabilities,
        serverInfo=Implementation(name="test-server", version="1.0.0")
    )
    
    mock_session = AsyncMock()
    mock_session.initialize.return_value = mock_initialize_result
    
    async def mock_execute(server_params, operation):
        return await operation(mock_session, mock_initialize_result)
    
    with patch.object(client, '_execute_with_session', side_effect=mock_execute):
        stdio_params = StdioServerParams(command="test", args=[])
        capabilities = await client.get_capabilities(stdio_params)
    
    assert isinstance(capabilities, ServerCapabilities)
    assert capabilities.tools is not None
    assert capabilities.resources is not None
    assert capabilities.prompts is not None


@pytest.mark.anyio
async def test_elicitation_callback_basic():
    """Test that elicitation callback is properly created and has expected structure"""
    from autogenstudio.web.routes.mcp import create_elicitation_callback
    from unittest.mock import AsyncMock
    
    mock_websocket = AsyncMock()
    session_id = "test-session-123"
    
    # Create the elicitation callback - it returns a tuple
    callback, pending_elicitations = create_elicitation_callback(mock_websocket, session_id)
    
    # Test that callback is callable
    assert callable(callback)
    
    # Test that pending_elicitations is a dict and starts empty
    assert isinstance(pending_elicitations, dict)
    assert len(pending_elicitations) == 0
    
    # Verify callback signature (should accept 2 parameters: context and params)
    import inspect
    sig = inspect.signature(callback)
    assert len(sig.parameters) == 2
    
    # Parameter names should be 'context' and 'params'
    param_names = list(sig.parameters.keys())
    assert param_names == ['context', 'params']


@pytest.mark.anyio 
async def test_elicitation_callback_creation():
    """Test that elicitation callback can be created with correct parameters"""
    from autogenstudio.web.routes.mcp import create_elicitation_callback
    from unittest.mock import AsyncMock
    
    mock_websocket = AsyncMock()
    session_id = "test-session-456"
    
    # Create the callback - it returns a tuple of (callback, pending_elicitations)
    callback, pending_elicitations = create_elicitation_callback(mock_websocket, session_id)
    
    # Verify callback is callable
    assert callable(callback)
    
    # Verify pending_elicitations is a dictionary
    assert isinstance(pending_elicitations, dict)
    assert len(pending_elicitations) == 0  # Should start empty
    
    # Verify callback has the expected signature by checking it accepts 2 parameters
    import inspect
    sig = inspect.signature(callback)
    assert len(sig.parameters) == 2
