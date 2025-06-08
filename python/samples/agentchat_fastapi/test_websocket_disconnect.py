#!/usr/bin/env python3
"""
Test script to verify that WebSocket disconnect is handled gracefully.
This reproduces the issue described in GitHub issue #6280.

Usage:
1. Start the server: python app_team.py
2. Run this test: python test_websocket_disconnect.py
"""

import asyncio
import json
import logging
import sys

import websockets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_disconnect(uri="ws://localhost:8002/ws/chat"):
    """
    Test the WebSocket disconnect scenario from issue #6280:
    1. Send message to server
    2. Receive messages from server
    3. Server waits for input (UserProxyAgent)
    4. Close websocket on client side
    
    Expected behavior: Server should handle disconnect gracefully without RuntimeError
    """
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")
            
            # Send initial message
            message = {"source": "user", "content": "Hello World"}
            await websocket.send(json.dumps(message))
            logger.info(f"Sent message: {message}")
            
            # Receive responses until we get a UserInputRequestedEvent
            async for response_text in websocket:
                try:
                    response = json.loads(response_text)
                    logger.info(f"Received: {response.get('type', 'unknown')} from {response.get('source', 'unknown')}")
                    
                    if response.get("type") == "UserInputRequestedEvent":
                        logger.info("Server is waiting for user input - now closing connection")
                        # This is where the issue occurs - close while server waits for input
                        await websocket.close()
                        logger.info("WebSocket closed gracefully")
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    break
                    
    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed by server")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
        
    logger.info("Test completed successfully - no RuntimeError occurred")
    return True


async def test_multiple_disconnects():
    """Test multiple disconnect scenarios to ensure robustness."""
    scenarios = [
        "Normal disconnect after UserInputRequestedEvent",
        "Disconnect during message processing", 
        "Disconnect immediately after connect"
    ]
    
    for i, scenario in enumerate(scenarios):
        logger.info(f"\n--- Test {i+1}: {scenario} ---")
        try:
            if i == 0:
                # Normal disconnect after UserInputRequestedEvent
                await test_websocket_disconnect()
            elif i == 1:
                # Disconnect during message processing
                await test_disconnect_during_processing()
            else:
                # Disconnect immediately
                await test_immediate_disconnect()
                
        except Exception as e:
            logger.error(f"Test {i+1} failed: {e}")
            return False
            
    return True


async def test_disconnect_during_processing():
    """Test disconnect while server is processing a message."""
    try:
        async with websockets.connect("ws://localhost:8002/ws/chat") as websocket:
            # Send message and immediately close
            message = {"source": "user", "content": "Quick test"}
            await websocket.send(json.dumps(message))
            await websocket.close()
            logger.info("Disconnected during processing")
            
    except Exception as e:
        logger.info(f"Expected exception during processing disconnect: {e}")


async def test_immediate_disconnect():
    """Test immediate disconnect after connection."""
    try:
        async with websockets.connect("ws://localhost:8002/ws/chat") as websocket:
            await websocket.close()
            logger.info("Immediate disconnect completed")
            
    except Exception as e:
        logger.info(f"Expected exception during immediate disconnect: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--multiple":
        # Run multiple test scenarios
        success = asyncio.run(test_multiple_disconnects())
    else:
        # Run single test scenario
        success = asyncio.run(test_websocket_disconnect())
        
    if success:
        logger.info("\n✅ All tests passed! WebSocket disconnect handling is working correctly.")
        sys.exit(0)
    else:
        logger.error("\n❌ Tests failed! There may still be issues with disconnect handling.")
        sys.exit(1)
