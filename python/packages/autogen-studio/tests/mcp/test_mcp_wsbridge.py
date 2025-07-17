#!/usr/bin/env python3
"""Test the MCPWebSocketBridge implementation"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fastapi import WebSocket
from mcp.types import ElicitResult, ErrorData

from autogenstudio.mcp.wsbridge import MCPWebSocketBridge
from autogenstudio.mcp.client import MCPClient


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages_sent = []
        self.messages_to_receive = []
        self.receive_index = 0
        # Use the actual enum value
        from fastapi.websockets import WebSocketState
        self.client_state = WebSocketState.CONNECTED
    
    async def send_json(self, data):
        self.messages_sent.append(data)
    
    async def receive_text(self):
        if self.receive_index < len(self.messages_to_receive):
            message = self.messages_to_receive[self.receive_index]
            self.receive_index += 1
            return message
        else:
            # Simulate WebSocket close
            raise Exception("WebSocket closed")
    
    def add_message(self, message):
        self.messages_to_receive.append(json.dumps(message) if isinstance(message, dict) else message)


class TestMCPWebSocketBridge:
    """Test the MCPWebSocketBridge class"""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        return MockWebSocket()
    
    @pytest.fixture
    def bridge(self, mock_websocket):
        """Create a MCPWebSocketBridge instance"""
        return MCPWebSocketBridge(mock_websocket, "test-session")
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, bridge, mock_websocket):
        """Test bridge initialization"""
        assert bridge.websocket == mock_websocket
        assert bridge.session_id == "test-session"
        assert bridge.mcp_client is None
        assert bridge.pending_elicitations == {}
        assert bridge._running is True
    
    @pytest.mark.asyncio
    async def test_send_message(self, bridge, mock_websocket):
        """Test message sending through WebSocket"""
        test_message = {
            "type": "test",
            "data": "test_data",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await bridge.send_message(test_message)
        
        assert len(mock_websocket.messages_sent) == 1
        assert mock_websocket.messages_sent[0]["type"] == "test"
        assert mock_websocket.messages_sent[0]["data"] == "test_data"
    
    @pytest.mark.asyncio
    async def test_on_initialized_event(self, bridge, mock_websocket):
        """Test on_initialized event handler"""
        capabilities = {"tools": True, "resources": True}
        
        await bridge.on_initialized("test-session", capabilities)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "initialized"
        assert message["session_id"] == "test-session"
        assert message["capabilities"] == capabilities
    
    @pytest.mark.asyncio
    async def test_on_operation_result_event(self, bridge, mock_websocket):
        """Test on_operation_result event handler"""
        operation = "list_tools"
        data = {"tools": [{"name": "test_tool"}]}
        
        await bridge.on_operation_result(operation, data)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "operation_result"
        assert message["operation"] == operation
        assert message["data"] == data
    
    @pytest.mark.asyncio
    async def test_on_operation_error_event(self, bridge, mock_websocket):
        """Test on_operation_error event handler"""
        operation = "call_tool"
        error = "Tool not found"
        
        await bridge.on_operation_error(operation, error)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "operation_error"
        assert message["operation"] == operation
        assert message["error"] == error
    
    @pytest.mark.asyncio
    async def test_on_elicitation_request_event(self, bridge, mock_websocket):
        """Test on_elicitation_request event handler"""
        request_id = "test-request-123"
        message_text = "Please provide input"
        schema = {"type": "string"}
        
        await bridge.on_elicitation_request(request_id, message_text, schema)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "elicitation_request"
        assert message["request_id"] == request_id
        assert message["message"] == message_text
        assert message["requestedSchema"] == schema
    
    @pytest.mark.asyncio
    async def test_set_mcp_client(self, bridge):
        """Test setting MCP client"""
        mock_client = MagicMock(spec=MCPClient)
        
        bridge.set_mcp_client(mock_client)
        
        assert bridge.mcp_client == mock_client
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, bridge, mock_websocket):
        """Test handling ping message"""
        ping_message = {"type": "ping"}
        
        await bridge.handle_websocket_message(ping_message)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "pong"
        assert "timestamp" in message
    
    @pytest.mark.asyncio
    async def test_handle_operation_message_without_client(self, bridge, mock_websocket):
        """Test handling operation message when MCP client is not set"""
        operation_message = {
            "type": "operation",
            "operation": "list_tools"
        }
        
        await bridge.handle_websocket_message(operation_message)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "error"
        assert "MCP client not initialized" in message["error"]
    
    @pytest.mark.asyncio
    async def test_handle_operation_message_with_client(self, bridge, mock_websocket):
        """Test handling operation message with MCP client"""
        # Set up mock client
        mock_client = AsyncMock(spec=MCPClient)
        bridge.set_mcp_client(mock_client)
        
        operation_message = {
            "type": "operation",
            "operation": "list_tools"
        }
        
        with patch('asyncio.create_task') as mock_create_task:
            await bridge.handle_websocket_message(operation_message)
            
            # Verify that create_task was called (async operation)
            mock_create_task.assert_called_once()
            
            # Verify the task was created with handle_operation call
            call_args = mock_create_task.call_args[0][0]
            # The task should be a coroutine, we can't easily verify the exact call
            # but we can verify create_task was called which is the critical behavior
    
    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, bridge, mock_websocket):
        """Test handling unknown message type"""
        unknown_message = {
            "type": "unknown_type",
            "data": "some_data"
        }
        
        await bridge.handle_websocket_message(unknown_message)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "error"
        assert "Unknown message type" in message["error"]
    
    @pytest.mark.asyncio
    async def test_handle_elicitation_response_accept(self, bridge, mock_websocket):
        """Test handling elicitation response with accept action"""
        # Set up pending elicitation
        request_id = "test-request-123"
        future = asyncio.Future()
        bridge.pending_elicitations[request_id] = future
        
        response_message = {
            "type": "elicitation_response",
            "request_id": request_id,
            "action": "accept",
            "data": {"input": "user response"}
        }
        
        # Handle the message in a task to avoid blocking
        async def handle_and_check():
            await bridge.handle_websocket_message(response_message)
            # Check that future was resolved
            assert future.done()
            result = future.result()
            assert isinstance(result, ElicitResult)
            assert result.action == "accept"
            assert result.content == {"input": "user response"}
        
        await handle_and_check()
    
    @pytest.mark.asyncio
    async def test_handle_elicitation_response_decline(self, bridge, mock_websocket):
        """Test handling elicitation response with decline action"""
        # Set up pending elicitation
        request_id = "test-request-456"
        future = asyncio.Future()
        bridge.pending_elicitations[request_id] = future
        
        response_message = {
            "type": "elicitation_response",
            "request_id": request_id,
            "action": "decline"
        }
        
        await bridge.handle_websocket_message(response_message)
        
        # Check that future was resolved
        assert future.done()
        result = future.result()
        assert isinstance(result, ElicitResult)
        assert result.action == "decline"
    
    @pytest.mark.asyncio
    async def test_handle_elicitation_response_missing_request_id(self, bridge, mock_websocket):
        """Test handling elicitation response with missing request_id"""
        response_message = {
            "type": "elicitation_response",
            "action": "accept",
            "data": {"input": "user response"}
        }
        
        await bridge.handle_websocket_message(response_message)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "error"
        assert "Missing request_id" in message["error"]
    
    @pytest.mark.asyncio
    async def test_handle_elicitation_response_unknown_request_id(self, bridge, mock_websocket):
        """Test handling elicitation response with unknown request_id"""
        response_message = {
            "type": "elicitation_response",
            "request_id": "unknown-request-id",
            "action": "accept",
            "data": {"input": "user response"}
        }
        
        await bridge.handle_websocket_message(response_message)
        
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "operation_error"
        assert "Unknown elicitation request_id" in message["error"]
    
    @pytest.mark.asyncio
    async def test_message_loop_with_valid_json(self, bridge, mock_websocket):
        """Test message loop with valid JSON messages"""
        # Add messages to receive
        mock_websocket.add_message({"type": "ping"})
        
        # Create a task to run the bridge and stop it after a short delay
        async def run_and_stop():
            await asyncio.sleep(0.1)  # Let it process one message
            bridge.stop()
        
        # Run both tasks concurrently
        await asyncio.gather(
            bridge.run(),
            run_and_stop(),
            return_exceptions=True
        )
        
        # Verify ping was handled
        assert len(mock_websocket.messages_sent) == 1
        assert mock_websocket.messages_sent[0]["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_message_loop_with_invalid_json(self, bridge, mock_websocket):
        """Test message loop with invalid JSON"""
        # Add invalid JSON message
        mock_websocket.add_message("invalid json {")
        
        # Create a task to run the bridge and stop it after a short delay
        async def run_and_stop():
            await asyncio.sleep(0.1)  # Let it process the invalid message
            bridge.stop()
        
        # Run both tasks concurrently
        await asyncio.gather(
            bridge.run(),
            run_and_stop(),
            return_exceptions=True
        )
        
        # Verify error message was sent
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == "error"
        assert "Invalid message format" in message["error"]
    
    def test_stop_bridge(self, bridge):
        """Test stopping the bridge"""
        assert bridge._running is True
        
        bridge.stop()
        
        assert bridge._running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
