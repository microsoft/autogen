#!/usr/bin/env python3
"""
Test script to verify elicitation callback implementation.

This script tests the elicitation callback functionality by mocking 
the components and verifying the flow works correctly.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.types import ElicitRequestParams, ElicitResult, ErrorData
from mcp.shared.context import RequestContext

# Import our elicitation callback creator
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Mock the send_websocket_message function since we can't easily import it
async def mock_send_websocket_message(websocket, message):
    """Mock version of send_websocket_message"""
    if hasattr(websocket, 'messages'):
        websocket.messages.append(message)
    return True


async def test_elicitation_logic():
    """Test the core elicitation callback logic"""
    
    print("🧪 Testing elicitation callback logic...")
    
    # Mock WebSocket with message storage
    mock_websocket = MagicMock()
    mock_websocket.messages = []
    
    session_id = "test-session-123"
    
    # Mock the send_websocket_message function
    with patch('autogenstudio.web.routes.mcp.send_websocket_message', side_effect=mock_send_websocket_message):
        from autogenstudio.web.routes.mcp import create_elicitation_callback
        
        # Create the elicitation callback
        elicitation_callback, pending_elicitations = create_elicitation_callback(mock_websocket, session_id)
        
        # Test 1: Create elicitation request
        print("\n📝 Test 1: Creating elicitation request")
        
        # Create mock context
        mock_context = MagicMock()
        
        # Create elicitation parameters  
        elicit_params = ElicitRequestParams(
            message="Please confirm this action",
            requestedSchema={"type": "object", "properties": {"confirm": {"type": "boolean"}}}
        )
        
        # Start the elicitation callback in a task
        elicitation_task = asyncio.create_task(
            elicitation_callback(mock_context, elicit_params)
        )
        
        # Wait a moment for the callback to process
        await asyncio.sleep(0.1)
        
        # Verify that messages were sent
        assert len(mock_websocket.messages) >= 2, f"Should send at least 2 messages, got {len(mock_websocket.messages)}"
        
        # Verify pending elicitations
        assert len(pending_elicitations) == 1, "Should have one pending elicitation"
        request_id = list(pending_elicitations.keys())[0]
        
        print(f"   ✅ Elicitation request created with ID: {request_id}")
        print(f"   ✅ Pending elicitations count: {len(pending_elicitations)}")
        print(f"   ✅ Messages sent: {len(mock_websocket.messages)}")
        
        # Test 2: User accepts the elicitation
        print("\n✅ Test 2: User accepts elicitation")
        
        # Simulate user acceptance
        user_response = ElicitResult(
            action="accept",
            content={"confirm": True}
        )
        
        # Resolve the pending future
        future = pending_elicitations[request_id]
        if not future.done():
            future.set_result(user_response)
        
        # Wait for the elicitation task to complete
        result = await elicitation_task
        
        # Verify the result
        assert isinstance(result, ElicitResult), f"Should return ElicitResult, got {type(result)}"
        assert result.action == "accept", f"Should have accept action, got {result.action}"
        assert result.content == {"confirm": True}, f"Should have correct content, got {result.content}"
        
        print(f"   ✅ Elicitation completed with action: {result.action}")
        print(f"   ✅ Content received: {result.content}")
        
        # Test 3: User declines elicitation
        print("\n❌ Test 3: User declines elicitation")
        
        # Reset for new test
        mock_websocket.messages.clear()
        
        # Create another elicitation
        elicitation_callback_2, pending_elicitations_2 = create_elicitation_callback(mock_websocket, session_id)
        
        elicitation_task_2 = asyncio.create_task(
            elicitation_callback_2(mock_context, elicit_params)
        )
        
        await asyncio.sleep(0.1)
        
        # Get request ID and simulate decline
        request_id_2 = list(pending_elicitations_2.keys())[0]
        decline_response = ElicitResult(action="decline")
        
        future_2 = pending_elicitations_2[request_id_2]
        if not future_2.done():
            future_2.set_result(decline_response)
        
        result_2 = await elicitation_task_2
        
        assert isinstance(result_2, ElicitResult), "Should return ElicitResult"
        assert result_2.action == "decline", "Should have decline action"
        
        print(f"   ✅ Decline handled correctly: {result_2.action}")
        
        print("\n🎉 Elicitation logic tests passed!")


async def test_message_formats():
    """Test that the correct message formats are generated"""
    
    print("\n📡 Testing message formats...")
    
    mock_websocket = MagicMock()
    mock_websocket.messages = []
    session_id = "test-format"
    
    with patch('autogenstudio.web.routes.mcp.send_websocket_message', side_effect=mock_send_websocket_message):
        from autogenstudio.web.routes.mcp import create_elicitation_callback
        
        elicitation_callback, pending_elicitations = create_elicitation_callback(mock_websocket, session_id)
        
        elicit_params = ElicitRequestParams(
            message="Test message format",
            requestedSchema={"type": "object", "properties": {"test": {"type": "string"}}}
        )
        
        # Start elicitation but cancel it quickly to just test message sending
        elicitation_task = asyncio.create_task(
            elicitation_callback(MagicMock(), elicit_params)
        )
        
        await asyncio.sleep(0.1)
        elicitation_task.cancel()
        
        try:
            await elicitation_task
        except asyncio.CancelledError:
            pass
        
        # Verify message formats
        messages = mock_websocket.messages
        assert len(messages) >= 2, f"Should send at least 2 messages, got {len(messages)}"
        
        # Check activity message
        activity_msg = messages[0]
        assert activity_msg["type"] == "mcp_activity", "First message should be activity"
        assert activity_msg["activity_type"] == "elicitation", "Should be elicitation activity"
        assert activity_msg["session_id"] == session_id, "Should have correct session ID"
        
        # Check elicitation request message
        request_msg = messages[1]
        assert request_msg["type"] == "elicitation_request", "Second message should be elicitation request"
        assert request_msg["message"] == "Test message format", "Should have correct message"
        assert request_msg["session_id"] == session_id, "Should have correct session ID"
        assert "request_id" in request_msg, "Should have request ID"
        assert "requestedSchema" in request_msg, "Should have requestedSchema"
        
        print("   ✅ Message formats are correct")
        print(f"   ✅ Activity message type: {activity_msg['type']}")
        print(f"   ✅ Request message type: {request_msg['type']}")


if __name__ == "__main__":
    print("Starting elicitation callback tests...")
    
    try:
        asyncio.run(test_elicitation_logic())
        asyncio.run(test_message_formats())
        print("\n🚀 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
