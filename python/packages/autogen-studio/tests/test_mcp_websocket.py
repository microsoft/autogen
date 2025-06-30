#!/usr/bin/env python3
"""Test the WebSocket MCP implementation"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import base64
from fastapi import WebSocket

from autogen_ext.tools.mcp._config import StdioServerParams
from mcp.types import (
    ListToolsResult, 
    Tool, 
    ServerCapabilities,
    ToolsCapability,
    ResourcesCapability,
    PromptsCapability,
    ListResourcesResult,
    Resource,
    ListPromptsResult,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
    TextContent,
    ReadResourceResult,
    TextResourceContents,
    CallToolResult
)


class TestMcpWebSocketRoutes:
    """Test MCP WebSocket routes with mocks"""
    
    @pytest.fixture
    def mock_server_params(self):
        """Create mock server parameters"""
        return StdioServerParams(
            command="test-command",
            args=["--test"],
            env={}
        )
    
    @pytest.fixture
    def mock_client_session(self):
        """Create a mock MCP client session"""
        mock_session = AsyncMock()
        
        # Mock initialization result
        mock_init_result = AsyncMock()
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
        mock_ws.client_state = "CONNECTED"  # Mock WebSocketState.CONNECTED
        return mock_ws
    
    @pytest.mark.asyncio
    async def test_send_websocket_message(self, mock_websocket):
        """Test WebSocket message sending"""
        from autogenstudio.web.routes.mcp import send_websocket_message
        
        test_message = {"type": "test", "data": "hello"}
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await send_websocket_message(mock_websocket, test_message)
            mock_websocket.send_json.assert_called_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_list_tools(self, mock_websocket, mock_client_session):
        """Test handling list_tools operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {"operation": "list_tools"}
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
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
    async def test_handle_mcp_operation_call_tool(self, mock_websocket, mock_client_session):
        """Test handling call_tool operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {
            "operation": "call_tool",
            "tool_name": "test_tool",
            "arguments": {"message": "hello"}
        }
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            # Verify the session method was called with correct arguments
            mock_client_session.call_tool.assert_called_once_with("test_tool", {"message": "hello"})
            
            # Verify WebSocket response was sent
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_result"
            assert sent_message["operation"] == "call_tool"
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_list_resources(self, mock_websocket, mock_client_session):
        """Test handling list_resources operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {"operation": "list_resources"}
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            mock_client_session.list_resources.assert_called_once()
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_result"
            assert sent_message["operation"] == "list_resources"
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_read_resource(self, mock_websocket, mock_client_session):
        """Test handling read_resource operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {
            "operation": "get_resource",
            "uri": "https://example.com/test.txt"
        }
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            mock_client_session.read_resource.assert_called_once_with("https://example.com/test.txt")
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_result"
            assert sent_message["operation"] == "read_resource"
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_list_prompts(self, mock_websocket, mock_client_session):
        """Test handling list_prompts operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {"operation": "list_prompts"}
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            mock_client_session.list_prompts.assert_called_once()
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_result"
            assert sent_message["operation"] == "list_prompts"
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_get_prompt(self, mock_websocket, mock_client_session):
        """Test handling get_prompt operation"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        operation = {
            "operation": "get_prompt",
            "name": "test_prompt",
            "arguments": {"input": "test"}
        }
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            mock_client_session.get_prompt.assert_called_once_with("test_prompt", {"input": "test"})
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_result"
            assert sent_message["operation"] == "get_prompt"
    
    @pytest.mark.asyncio
    async def test_handle_mcp_operation_error_handling(self, mock_websocket, mock_client_session):
        """Test error handling in MCP operations"""
        from autogenstudio.web.routes.mcp import handle_mcp_operation
        
        # Make the session raise an exception
        mock_client_session.list_tools.side_effect = Exception("Test error")
        
        operation = {"operation": "list_tools"}
        
        with patch('fastapi.websockets.WebSocketState') as mock_state:
            mock_state.CONNECTED = "CONNECTED"
            await handle_mcp_operation(mock_websocket, mock_client_session, operation)
            
            # Verify operation error response was sent (not connection error)
            mock_websocket.send_json.assert_called_once()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "operation_error"
            assert sent_message["operation"] == "list_tools"
            assert "Test error" in sent_message["error"]
    
    def test_websocket_connection_url_generation(self, mock_server_params):
        """Test WebSocket connection URL generation"""
        session_id = "test-session-123"
        
        # Test the URL generation logic
        server_params_json = json.dumps(mock_server_params.model_dump())
        encoded_params = base64.b64encode(server_params_json.encode()).decode()
        expected_url = f"/api/mcp/ws/{session_id}?server_params={encoded_params}"
        
        assert session_id in expected_url
        assert "server_params=" in expected_url
        assert expected_url.startswith("/api/mcp/ws/")
    
    def test_active_sessions_structure(self):
        """Test active sessions data structure"""
        from autogenstudio.web.routes.mcp import active_sessions
        
        # Test that active_sessions is a dictionary
        assert isinstance(active_sessions, dict)
        
        # Test the structure we expect for session data
        test_session_id = "test-123"
        from datetime import datetime, timezone
        
        expected_structure = {
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "capabilities": None
        }
        
        # Test that we can add and retrieve session data
        active_sessions[test_session_id] = expected_structure
        assert test_session_id in active_sessions
        assert "created_at" in active_sessions[test_session_id]
        assert "last_activity" in active_sessions[test_session_id]
        assert "capabilities" in active_sessions[test_session_id]
        
        # Clean up
        active_sessions.pop(test_session_id, None)


class TestMcpRouteIntegration:
    """Integration tests for MCP routes"""
    
    def test_router_exists(self):
        """Test that the MCP router exists"""
        from autogenstudio.web.routes.mcp import router
        
        assert router is not None
        
        # Test that the router has routes defined
        assert hasattr(router, 'routes')
        assert len(router.routes) > 0
        
        # Test that we can access basic router properties
        assert hasattr(router, 'include_in_schema')
        assert hasattr(router, 'tags')
    
    def test_create_websocket_connection_request_model(self):
        """Test the CreateWebSocketConnectionRequest model"""
        from autogenstudio.web.routes.mcp import CreateWebSocketConnectionRequest
        from autogen_ext.tools.mcp._config import StdioServerParams
        
        server_params = StdioServerParams(
            command="test-command",
            args=["--test"],
            env={}
        )
        
        request = CreateWebSocketConnectionRequest(server_params=server_params)
        assert request.server_params == server_params
