"""
Updated tests for MCP WebSocket functionality using the new refactored architecture.
These tests replace the failing legacy tests in test_mcp_websocket.py.
"""

import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import WebSocket

# Import the new architecture components
from autogenstudio.mcp.client import MCPClient
from autogenstudio.mcp.wsbridge import MCPWebSocketBridge

# Import MCP types for mocking
from mcp.types import (
    Tool, Resource, Prompt, PromptArgument,
    ListToolsResult, CallToolResult, ListResourcesResult, 
    ReadResourceResult, ListPromptsResult, GetPromptResult,
    TextContent, TextResourceContents, PromptMessage,
    ServerCapabilities, ToolsCapability, ResourcesCapability, PromptsCapability
)
from autogen_ext.tools.mcp._config import StdioServerParams


class TestMCPWebSocketUpdated:
    """Updated tests for MCP WebSocket functionality"""
    
    @pytest.fixture
    def mock_server_params(self):
        """Create mock server parameters"""
        return StdioServerParams(
            command="node",
            args=["server.js"],
            env={"NODE_ENV": "test"}
        )
    
    @pytest.fixture
    def mock_client_session(self):
        """Create a mock MCP client session with all necessary methods"""
        mock_session = AsyncMock()
        
        # Mock initialization result
        mock_init_result = MagicMock()
        mock_init_result.capabilities = ServerCapabilities(
            tools=ToolsCapability(listChanged=False),
            resources=ResourcesCapability(subscribe=False, listChanged=False),
            prompts=PromptsCapability(listChanged=False)
        )
        mock_session.initialize.return_value = mock_init_result
        
        # Mock tools
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
        
        # Mock call tool result
        mock_call_result = CallToolResult(
            content=[TextContent(type="text", text="Tool executed successfully")],
            isError=False
        )
        mock_session.call_tool.return_value = mock_call_result
        
        # Mock resources
        from pydantic import HttpUrl
        test_uri = HttpUrl("https://example.com/test.txt")
        mock_resources = [
            Resource(
                uri=test_uri,
                name="test.txt",
                description="A test resource",
                mimeType="text/plain"
            )
        ]
        mock_session.list_resources.return_value = ListResourcesResult(resources=mock_resources)
        
        # Mock resource content
        mock_resource_content = ReadResourceResult(
            contents=[TextResourceContents(
                uri=test_uri,
                text="This is test content",
                mimeType="text/plain"
            )]
        )
        mock_session.read_resource.return_value = mock_resource_content
        
        # Mock prompts
        mock_prompts = [
            Prompt(
                name="test_prompt",
                description="A test prompt",
                arguments=[
                    PromptArgument(
                        name="input",
                        description="Input text",
                        required=True
                    )
                ]
            )
        ]
        mock_session.list_prompts.return_value = ListPromptsResult(prompts=mock_prompts)
        
        # Mock prompt result
        mock_prompt_result = GetPromptResult(
            description="Test prompt result",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text="Test message")
                )
            ]
        )
        mock_session.get_prompt.return_value = mock_prompt_result
        
        return mock_session
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        mock_ws = AsyncMock(spec=WebSocket)
        from fastapi.websockets import WebSocketState
        mock_ws.client_state = WebSocketState.CONNECTED
        return mock_ws

    @pytest.mark.asyncio
    async def test_websocket_bridge_send_message(self, mock_websocket):
        """Test WebSocket message sending via MCPWebSocketBridge"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        test_message = {"type": "test", "data": "hello"}
        
        await bridge.send_message(test_message)
        mock_websocket.send_json.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_mcp_client_list_tools_operation(self, mock_websocket, mock_client_session):
        """Test handling list_tools operation via MCPClient"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        client = MCPClient(mock_client_session, "test_session", bridge)
        
        operation = {"operation": "list_tools"}
        
        await client.handle_operation(operation)
        
        # Verify the session method was called
        mock_client_session.list_tools.assert_called_once()
        
        # Verify WebSocket response was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "operation_result"
        assert sent_message["operation"] == "list_tools"
        assert "data" in sent_message
        assert "tools" in sent_message["data"]

    @pytest.mark.asyncio
    async def test_mcp_client_call_tool_operation(self, mock_websocket, mock_client_session):
        """Test handling call_tool operation via MCPClient"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        client = MCPClient(mock_client_session, "test_session", bridge)
        
        operation = {
            "operation": "call_tool",
            "tool_name": "test_tool",
            "arguments": {"message": "hello"}
        }
        
        await client.handle_operation(operation)
        
        # Verify the session method was called with correct arguments
        mock_client_session.call_tool.assert_called_once_with("test_tool", {"message": "hello"})
        
        # Verify WebSocket response was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "operation_result"
        assert sent_message["operation"] == "call_tool"

    @pytest.mark.asyncio
    async def test_mcp_client_list_resources_operation(self, mock_websocket, mock_client_session):
        """Test handling list_resources operation via MCPClient"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        client = MCPClient(mock_client_session, "test_session", bridge)
        
        operation = {"operation": "list_resources"}
        
        await client.handle_operation(operation)
        
        mock_client_session.list_resources.assert_called_once()
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "operation_result"
        assert sent_message["operation"] == "list_resources"

    @pytest.mark.asyncio
    async def test_mcp_client_read_resource_operation(self, mock_websocket, mock_client_session):
        """Test handling read_resource operation via MCPClient"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        client = MCPClient(mock_client_session, "test_session", bridge)
        
        operation = {
            "operation": "read_resource",
            "uri": "https://example.com/test.txt"
        }
        
        await client.handle_operation(operation)
        
        mock_client_session.read_resource.assert_called_once_with("https://example.com/test.txt")
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "operation_result"
        assert sent_message["operation"] == "read_resource"

    @pytest.mark.asyncio
    async def test_mcp_client_error_handling(self, mock_websocket, mock_client_session):
        """Test error handling in MCP operations via MCPClient"""
        bridge = MCPWebSocketBridge(mock_websocket, "test_session")
        client = MCPClient(mock_client_session, "test_session", bridge)
        
        # Make the session raise an exception
        mock_client_session.list_tools.side_effect = Exception("Test error")
        
        operation = {"operation": "list_tools"}
        
        await client.handle_operation(operation)
        
        # Verify operation error response was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "operation_error"
        assert sent_message["operation"] == "list_tools"
        assert "Test error" in sent_message["error"]

    def test_websocket_connection_url_generation(self, mock_server_params):
        """Test WebSocket connection URL generation (preserved from original tests)"""
        session_id = "test-session-123"
        
        # Test the URL generation logic
        server_params_json = json.dumps(mock_server_params.model_dump())
        encoded_params = base64.b64encode(server_params_json.encode()).decode()
        
        expected_url = f"ws://localhost:8000/ws/mcp?session_id={session_id}&server_params={encoded_params}"
        
        # This is a functional test - just verify the encoding/decoding works
        decoded_params = base64.b64decode(encoded_params.encode()).decode()
        decoded_obj = json.loads(decoded_params)
        
        assert decoded_obj["command"] == "node"
        assert decoded_obj["args"] == ["server.js"]
        assert decoded_obj["env"]["NODE_ENV"] == "test"

    def test_active_sessions_structure(self):
        """Test active sessions data structure (preserved from original tests)"""
        from autogenstudio.web.routes.mcp import active_sessions
        
        # Test that active_sessions is a dictionary
        assert isinstance(active_sessions, dict)
        
        # Test adding a session
        session_id = "test-session"
        session_data = {
            "session_id": session_id,
            "server_params": {"command": "node", "args": ["server.js"]},
            "last_activity": "2023-01-01T00:00:00Z",
            "status": "active"
        }
        
        active_sessions[session_id] = session_data
        assert session_id in active_sessions
        assert active_sessions[session_id] == session_data
        
        # Clean up
        del active_sessions[session_id]


class TestMCPRouteIntegrationUpdated:
    """Updated integration tests for MCP routes"""
    
    def test_router_exists(self):
        """Test that the MCP router exists and is properly configured"""
        from autogenstudio.web.routes.mcp import router
        from fastapi import APIRouter
        
        assert isinstance(router, APIRouter)

    def test_create_websocket_connection_request_model(self):
        """Test the request model for creating WebSocket connections"""
        from autogenstudio.web.routes.mcp import CreateWebSocketConnectionRequest
        from autogen_ext.tools.mcp._config import StdioServerParams
        
        # Test creating a request with valid server params
        server_params = StdioServerParams(
            command="node",
            args=["server.js"],
            env={"NODE_ENV": "test"}
        )
        
        request = CreateWebSocketConnectionRequest(server_params=server_params)
        assert request.server_params == server_params
        # Type-check that server_params is StdioServerParams
        assert isinstance(request.server_params, StdioServerParams)
        assert request.server_params.command == "node"
        assert request.server_params.args == ["server.js"]
