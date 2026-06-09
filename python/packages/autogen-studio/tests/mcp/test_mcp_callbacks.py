#!/usr/bin/env python3
"""Test the refactored MCP callback functions"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from typing import Any

from mcp.types import (
    CreateMessageRequestParams,
    CreateMessageResult,
    ElicitRequestParams,
    ElicitResult,
    ErrorData,
    TextContent
)
from mcp.shared.context import RequestContext

from autogenstudio.mcp.callbacks import (
    create_message_handler,
    create_sampling_callback,
    create_elicitation_callback
)
from autogenstudio.mcp.wsbridge import MCPWebSocketBridge


class MockBridge(MCPWebSocketBridge):
    """Mock bridge for testing callbacks"""
    
    def __init__(self):
        # Don't call parent __init__ to avoid WebSocket dependency
        self.session_id = "test-session"
        self.pending_elicitations = {}
        self.events = []
    
    async def on_mcp_activity(self, activity_type: str, message: str, details: dict) -> None:
        self.events.append(("mcp_activity", activity_type, message, details))
    
    async def on_elicitation_request(self, request_id: str, message: str, requested_schema: Any) -> None:
        self.events.append(("elicitation_request", request_id, message, requested_schema))


class TestMCPCallbacks:
    """Test MCP callback functions"""
    
    @pytest.fixture
    def mock_bridge(self):
        """Create a mock bridge"""
        return MockBridge()
    
    @pytest.mark.asyncio
    async def test_message_handler_with_exception(self, mock_bridge):
        """Test message handler with exception"""
        handler = create_message_handler(mock_bridge)
        
        test_exception = Exception("Test protocol error")
        await handler(test_exception)
        
        # Verify activity was logged
        assert len(mock_bridge.events) == 1
        event = mock_bridge.events[0]
        assert event[0] == "mcp_activity"
        assert event[1] == "error"
        assert "Protocol error" in event[2]
        assert "Test protocol error" in event[3]["details"]
    
    @pytest.mark.asyncio
    async def test_message_handler_with_method_message(self, mock_bridge):
        """Test message handler with method-based message"""
        handler = create_message_handler(mock_bridge)
        
        # Create a mock message with method attribute
        mock_message = MagicMock()
        mock_message.method = "notifications/initialized"
        mock_message.params = {"capabilities": {"tools": True}}
        
        await handler(mock_message)
        
        # Verify activity was logged
        assert len(mock_bridge.events) == 1
        event = mock_bridge.events[0]
        assert event[0] == "mcp_activity"
        assert event[1] == "protocol"
        assert "notifications/initialized" in event[2]
        assert event[3]["method"] == "notifications/initialized"
    
    @pytest.mark.asyncio
    async def test_message_handler_with_other_message(self, mock_bridge):
        """Test message handler with other message types"""
        handler = create_message_handler(mock_bridge)
        
        # Create a simple mock message without method, avoiding recursion issues
        class SimpleMockMessage:
            def model_dump(self):
                return {"type": "response", "data": "test"}
        
        mock_message = SimpleMockMessage()
        
        # Type ignore for test purposes - we're testing edge case handling
        await handler(mock_message)  # type: ignore
        
        # Verify activity was logged
        assert len(mock_bridge.events) == 1
        event = mock_bridge.events[0]
        assert event[0] == "mcp_activity"
        assert event[1] == "protocol"
        assert "SimpleMockMessage" in event[2]  # Type name
    
    @pytest.mark.asyncio
    async def test_sampling_callback_success(self, mock_bridge):
        """Test sampling callback success case"""
        callback = create_sampling_callback(mock_bridge)
        
        # Create mock context and params
        mock_context = AsyncMock(spec=RequestContext)
        mock_params = CreateMessageRequestParams(
            messages=[],  # Empty messages array for test
            maxTokens=100
        )
        
        result = await callback(mock_context, mock_params)
        
        # Verify result is CreateMessageResult
        assert isinstance(result, CreateMessageResult)
        assert result.role == "assistant"
        assert result.model == "autogen-studio-default"
        assert isinstance(result.content, TextContent)
        assert "AutoGen Studio Default Sampling Response" in result.content.text
        
        # Verify activities were logged
        assert len(mock_bridge.events) == 2
        # First event: sampling request
        assert mock_bridge.events[0][1] == "sampling"
        assert "Tool requested AI sampling" in mock_bridge.events[0][2]
        # Second event: sampling response
        assert mock_bridge.events[1][1] == "sampling"
        assert "Provided default sampling response" in mock_bridge.events[1][2]
    
    @pytest.mark.asyncio
    async def test_sampling_callback_exception(self, mock_bridge):
        """Test sampling callback with exception"""
        callback = create_sampling_callback(mock_bridge)
        
        # Create mock context that raises exception
        mock_context = AsyncMock(spec=RequestContext)
        
        # Create params that will cause an exception when accessing
        mock_params = MagicMock()
        mock_params.messages = None  # This should cause an error
        
        # Mock the model_dump to raise exception
        mock_params.model_dump.side_effect = Exception("Test sampling error")
        
        result = await callback(mock_context, mock_params)
        
        # Verify result is ErrorData
        assert isinstance(result, ErrorData)
        assert result.code == -32603
        assert "Sampling failed" in result.message
        
        # Verify error was logged
        error_events = [e for e in mock_bridge.events if e[1] == "error"]
        assert len(error_events) == 1
        assert "Sampling callback error" in error_events[0][2]
    
    @pytest.mark.asyncio
    async def test_elicitation_callback_success(self, mock_bridge):
        """Test elicitation callback success case"""
        callback, pending_dict = create_elicitation_callback(mock_bridge)
        
        # Verify that pending_dict is the same as bridge's pending_elicitations
        assert pending_dict is mock_bridge.pending_elicitations
        
        # Create mock context and params
        mock_context = AsyncMock(spec=RequestContext)
        mock_params = ElicitRequestParams(
            message="Please provide your name",
            requestedSchema={"type": "string"}
        )
        
        # Create a task to simulate user response
        async def simulate_user_response():
            await asyncio.sleep(0.1)  # Let elicitation setup
            
            # Find the request ID from events
            elicit_events = [e for e in mock_bridge.events if e[0] == "elicitation_request"]
            assert len(elicit_events) == 1
            request_id = elicit_events[0][1]
            
            # Simulate user accepting
            if request_id in mock_bridge.pending_elicitations:
                future = mock_bridge.pending_elicitations[request_id]
                result = ElicitResult(action="accept", content={"name": "John Doe"})
                future.set_result(result)
        
        # Run both the callback and the response simulation
        callback_task = asyncio.create_task(callback(mock_context, mock_params))
        response_task = asyncio.create_task(simulate_user_response())
        
        result, _ = await asyncio.gather(callback_task, response_task)
        
        # Verify result
        assert isinstance(result, ElicitResult)
        assert result.action == "accept"
        assert result.content == {"name": "John Doe"}
        
        # Verify events were logged
        activity_events = [e for e in mock_bridge.events if e[0] == "mcp_activity"]
        elicit_events = [e for e in mock_bridge.events if e[0] == "elicitation_request"]
        
        assert len(elicit_events) == 1
        assert len(activity_events) >= 2  # Request and response activities
    
    @pytest.mark.asyncio
    async def test_elicitation_callback_timeout(self, mock_bridge):
        """Test elicitation callback timeout"""
        callback, _ = create_elicitation_callback(mock_bridge)
        
        # Create mock context and params
        mock_context = AsyncMock(spec=RequestContext)
        mock_params = ElicitRequestParams(
            message="Please provide input",
            requestedSchema={"type": "string"}
        )
        
        # Mock asyncio.wait_for to raise TimeoutError
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            result = await callback(mock_context, mock_params)
        
        # Verify result is ErrorData
        assert isinstance(result, ErrorData)
        assert result.code == -32603
        assert "60 seconds" in result.message
        
        # Verify timeout was logged
        error_events = [e for e in mock_bridge.events if e[1] == "error"]
        assert len(error_events) == 1
        assert "Elicitation timeout" in error_events[0][2]
    
    @pytest.mark.asyncio
    async def test_elicitation_callback_exception(self, mock_bridge):
        """Test elicitation callback with exception"""
        callback, _ = create_elicitation_callback(mock_bridge)
        
        # Create mock context and params that will cause exception
        mock_context = AsyncMock(spec=RequestContext)
        mock_params = MagicMock()
        mock_params.message = "Test message"
        mock_params.requestedSchema = None
        
        # Mock uuid.uuid4 to raise exception
        with patch('uuid.uuid4', side_effect=Exception("UUID generation failed")):
            result = await callback(mock_context, mock_params)
        
        # Verify result is ErrorData
        assert isinstance(result, ErrorData)
        assert result.code == -32603
        assert "Elicitation failed" in result.message
        
        # Verify error was logged
        error_events = [e for e in mock_bridge.events if e[1] == "error"]
        assert len(error_events) == 1
        assert "Elicitation callback error" in error_events[0][2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
