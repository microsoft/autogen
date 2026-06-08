#!/usr/bin/env python3
"""Test the integration of all MCP components"""

import asyncio
import json
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fastapi import WebSocket
from autogen_ext.tools.mcp._config import StdioServerParams

from autogenstudio.mcp.client import MCPClient
from autogenstudio.mcp.wsbridge import MCPWebSocketBridge
from autogenstudio.mcp.callbacks import create_message_handler, create_sampling_callback, create_elicitation_callback
from autogenstudio.mcp.utils import extract_real_error, serialize_for_json, is_websocket_disconnect, McpOperationError


class TestMCPIntegration:
    """Test integration of MCP components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_operation_flow(self):
        """Test complete operation flow from WebSocket to MCP client"""
        # Create mock WebSocket
        mock_websocket = MagicMock(spec=WebSocket)
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.send_json = AsyncMock()
        
        # Create bridge
        bridge = MCPWebSocketBridge(mock_websocket, "test-session")
        
        # Create mock MCP session
        mock_session = AsyncMock()
        mock_session.initialize.return_value = AsyncMock()
        mock_session.initialize.return_value.capabilities = AsyncMock()
        mock_session.list_tools.return_value = AsyncMock()
        mock_session.list_tools.return_value.tools = []
        
        # Create and set MCP client
        client = MCPClient(mock_session, "test-session", bridge)
        bridge.set_mcp_client(client)
        
        # Initialize client
        await client.initialize()
        
        # Test operation flow
        operation_message = {
            "type": "operation",
            "operation": "list_tools"
        }
        
        # Handle the operation (should run in background task)
        await bridge.handle_websocket_message(operation_message)
        
        # Give background task time to complete
        await asyncio.sleep(0.1)
        
        # Verify session method was called
        mock_session.list_tools.assert_called_once()
        
        # Verify WebSocket messages were sent
        assert mock_websocket.send_json.call_count >= 2  # initialized + operation_result
    
    @pytest.mark.asyncio
    async def test_elicitation_integration(self):
        """Test elicitation flow integration"""
        # Create mock WebSocket
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client_state = "CONNECTED"
        mock_websocket.send_json = AsyncMock()
        
        # Create bridge
        bridge = MCPWebSocketBridge(mock_websocket, "test-session")
        
        # Create elicitation callback
        elicitation_callback, pending_dict = create_elicitation_callback(bridge)
        
        # Verify that pending_dict is the bridge's pending_elicitations
        assert pending_dict is bridge.pending_elicitations
        
        # Test that bridge can handle elicitation responses
        assert hasattr(bridge, 'pending_elicitations')
        assert isinstance(bridge.pending_elicitations, dict)


class TestMCPUtils:
    """Test MCP utility functions"""
    
    def test_extract_real_error_simple(self):
        """Test extract_real_error with simple exception"""
        error = ValueError("Test error message")
        result = extract_real_error(error)
        assert "ValueError: Test error message" in result
    
    def test_extract_real_error_chained(self):
        """Test extract_real_error with chained exceptions"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapper error") from e
        except RuntimeError as e:
            result = extract_real_error(e)
            assert "RuntimeError: Wrapper error" in result
            assert "ValueError: Original error" in result
    
    def test_extract_real_error_with_context(self):
        """Test extract_real_error with context exceptions"""
        try:
            try:
                raise ValueError("Context error")
            except ValueError:
                raise RuntimeError("Main error")
        except RuntimeError as e:
            result = extract_real_error(e)
            assert "RuntimeError: Main error" in result
            assert "ValueError: Context error" in result
    
    def test_serialize_for_json_simple_types(self):
        """Test serialize_for_json with simple types"""
        assert serialize_for_json("string") == "string"
        assert serialize_for_json(42) == 42
        assert serialize_for_json(True) is True
        assert serialize_for_json(None) is None
    
    def test_serialize_for_json_dict(self):
        """Test serialize_for_json with dictionary"""
        data = {
            "string": "value",
            "number": 42,
            "bool": True,
            "nested": {"inner": "value"}
        }
        result = serialize_for_json(data)
        assert result == {
            "string": "value",
            "number": 42,
            "bool": True,
            "nested": {"inner": "value"}
        }
    
    def test_serialize_for_json_list(self):
        """Test serialize_for_json with list"""
        data = ["string", 42, True, {"nested": "value"}]
        result = serialize_for_json(data)
        assert result == ["string", 42, True, {"nested": "value"}]
    
    def test_serialize_for_json_with_model_dump(self):
        """Test serialize_for_json with object that has model_dump"""
        mock_obj = MagicMock()
        mock_obj.model_dump.return_value = {"key": "value"}
        
        result = serialize_for_json(mock_obj)
        assert result == {"key": "value"}
        mock_obj.model_dump.assert_called_once()
    
    def test_serialize_for_json_with_anyurl(self):
        """Test serialize_for_json with AnyUrl"""
        from pydantic import HttpUrl
        url = HttpUrl("https://example.com/test")
        result = serialize_for_json(url)
        assert result == "https://example.com/test"
    
    def test_is_websocket_disconnect_with_websocket_disconnect(self):
        """Test is_websocket_disconnect with WebSocketDisconnect"""
        from fastapi import WebSocketDisconnect
        error = WebSocketDisconnect(code=1000, reason="Normal closure")
        assert is_websocket_disconnect(error) is True
    
    def test_is_websocket_disconnect_with_regular_exception(self):
        """Test is_websocket_disconnect with regular exception"""
        error = ValueError("Regular error")
        assert is_websocket_disconnect(error) is False
    
    def test_is_websocket_disconnect_with_nested_exception(self):
        """Test is_websocket_disconnect with nested WebSocketDisconnect"""
        from fastapi import WebSocketDisconnect
        
        # Create a nested exception structure
        try:
            try:
                raise WebSocketDisconnect(code=1000, reason="Normal closure")
            except WebSocketDisconnect as e:
                raise RuntimeError("Wrapper") from e
        except RuntimeError as e:
            assert is_websocket_disconnect(e) is True
    
    def test_is_websocket_disconnect_with_no_status_rcvd(self):
        """Test is_websocket_disconnect with NO_STATUS_RCVD message"""
        error = Exception("Connection closed with NO_STATUS_RCVD")
        assert is_websocket_disconnect(error) is True
    
    def test_is_websocket_disconnect_with_websocket_in_name(self):
        """Test is_websocket_disconnect with WebSocket in exception name"""
        class CustomWebSocketDisconnectError(Exception):
            pass
        
        error = CustomWebSocketDisconnectError("Custom disconnect")
        assert is_websocket_disconnect(error) is True
    
    def test_mcp_operation_error(self):
        """Test McpOperationError exception"""
        error = McpOperationError("Test operation failed")
        assert str(error) == "Test operation failed"
        assert isinstance(error, Exception)


class TestMCPRouteIntegration:
    """Test integration with route components"""
    
    def test_server_params_serialization(self):
        """Test that server params can be serialized/deserialized correctly"""
        server_params = StdioServerParams(
            command="test-command",
            args=["--arg1", "value1"],
            env={"ENV_VAR": "value"}
        )
        
        # Test serialization
        serialized = serialize_for_json(server_params.model_dump())
        assert isinstance(serialized, dict)
        assert serialized["command"] == "test-command"
        assert serialized["args"] == ["--arg1", "value1"]
        assert serialized["env"] == {"ENV_VAR": "value"}
    
    def test_websocket_url_encoding(self):
        """Test WebSocket URL parameter encoding"""
        server_params = StdioServerParams(
            command="test-command",
            args=["--test"],
            env={}
        )
        
        # Simulate the encoding process from the route
        server_params_json = json.dumps(serialize_for_json(server_params.model_dump()))
        server_params_encoded = base64.b64encode(server_params_json.encode("utf-8")).decode("utf-8")
        
        # Test decoding
        decoded_params = base64.b64decode(server_params_encoded).decode("utf-8")
        server_params_dict = json.loads(decoded_params)
        
        assert server_params_dict["command"] == "test-command"
        assert server_params_dict["args"] == ["--test"]
        assert server_params_dict["env"] == {}
        assert server_params_dict["type"] == "StdioServerParams"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
