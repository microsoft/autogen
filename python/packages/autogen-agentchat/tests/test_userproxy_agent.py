import asyncio
from typing import Optional, Sequence

import pytest
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, HandoffMessage, TextMessage
from autogen_core import CancellationToken


@pytest.mark.asyncio
async def test_basic_input() -> None:
    """Test basic message handling with custom input"""

    def custom_input(prompt: str) -> str:
        return "The height of the eiffel tower is 324 meters. Aloha!"

    agent = UserProxyAgent(name="test_user", input_func=custom_input)
    messages = [TextMessage(content="What is the height of the eiffel tower?", source="assistant")]

    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content == "The height of the eiffel tower is 324 meters. Aloha!"
    assert response.chat_message.source == "test_user"


@pytest.mark.asyncio
async def test_async_input() -> None:
    """Test handling of async input function"""

    async def async_input(prompt: str, token: Optional[CancellationToken] = None) -> str:
        await asyncio.sleep(0.1)
        return "async response"

    agent = UserProxyAgent(name="test_user", input_func=async_input)
    messages = [TextMessage(content="test prompt", source="assistant")]

    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content == "async response"
    assert response.chat_message.source == "test_user"


@pytest.mark.asyncio
async def test_handoff_handling() -> None:
    """Test handling of handoff messages"""

    def custom_input(prompt: str) -> str:
        return "handoff response"

    agent = UserProxyAgent(name="test_user", input_func=custom_input)

    messages: Sequence[BaseChatMessage] = [
        TextMessage(content="Initial message", source="assistant"),
        HandoffMessage(content="Handing off to user for confirmation", source="assistant", target="test_user"),
    ]

    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response.chat_message, HandoffMessage)
    assert response.chat_message.content == "handoff response"
    assert response.chat_message.source == "test_user"
    assert response.chat_message.target == "assistant"

    # The latest message if is a handoff message, it must be addressed to this agent.
    messages = [
        TextMessage(content="Initial message", source="assistant"),
        HandoffMessage(content="Handing off to user for confirmation", source="assistant", target="other_agent"),
    ]
    with pytest.raises(RuntimeError):
        await agent.on_messages(messages, CancellationToken())

    # No handoff message if the latest message is not a handoff message addressed to this agent.
    messages = [
        TextMessage(content="Initial message", source="assistant"),
        HandoffMessage(content="Handing off to other agent", source="assistant", target="other_agent"),
        TextMessage(content="Another message", source="other_agent"),
    ]
    response = await agent.on_messages(messages, CancellationToken())
    assert isinstance(response.chat_message, TextMessage)


@pytest.mark.asyncio
async def test_cancellation() -> None:
    """Test cancellation during message handling"""

    async def cancellable_input(prompt: str, token: Optional[CancellationToken] = None) -> str:
        await asyncio.sleep(0.1)
        if token and token.is_cancelled():
            raise asyncio.CancelledError()
        return "cancellable response"

    agent = UserProxyAgent(name="test_user", input_func=cancellable_input)
    messages = [TextMessage(content="test prompt", source="assistant")]
    token = CancellationToken()

    async def cancel_after_delay() -> None:
        await asyncio.sleep(0.05)
        token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(agent.on_messages(messages, token), cancel_after_delay())


@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test error handling with problematic input function"""

    def failing_input(_: str) -> str:
        raise ValueError("Input function failed")

    agent = UserProxyAgent(name="test_user", input_func=failing_input)
    messages = [TextMessage(content="test prompt", source="assistant")]

    with pytest.raises(RuntimeError) as exc_info:
        await agent.on_messages(messages, CancellationToken())
    assert "Failed to get user input" in str(exc_info.value)


@pytest.mark.asyncio
async def test_websocket_exception_propagation() -> None:
    """Test that WebSocket-related exceptions are properly propagated instead of being wrapped in RuntimeError"""

    class MockWebSocketDisconnect(Exception):
        """Mock WebSocketDisconnect exception to simulate FastAPI's WebSocketDisconnect"""
        def __init__(self, code: int = 1000, reason: str = ""):
            self.code = code
            self.reason = reason
            super().__init__(f"WebSocket disconnected with code {code}: {reason}")

    class MockConnectionClosedError(Exception):
        """Mock ConnectionClosedError exception to simulate websockets library exception"""
        pass

    def websocket_disconnect_input(_: str) -> str:
        # Simulate WebSocketDisconnect by creating an exception with the right class name
        exc = MockWebSocketDisconnect(1000, "Client disconnected")
        exc.__class__.__name__ = "WebSocketDisconnect"
        raise exc

    def connection_closed_input(_: str) -> str:
        # Simulate ConnectionClosedError by creating an exception with the right class name
        exc = MockConnectionClosedError("Connection closed")
        exc.__class__.__name__ = "ConnectionClosedError"
        raise exc

    agent = UserProxyAgent(name="test_user", input_func=websocket_disconnect_input)
    messages = [TextMessage(content="test prompt", source="assistant")]

    # WebSocketDisconnect should be propagated, not wrapped in RuntimeError
    with pytest.raises(MockWebSocketDisconnect):
        await agent.on_messages(messages, CancellationToken())

    agent2 = UserProxyAgent(name="test_user", input_func=connection_closed_input)
    
    # ConnectionClosedError should be propagated, not wrapped in RuntimeError
    with pytest.raises(MockConnectionClosedError):
        await agent2.on_messages(messages, CancellationToken())

    # Test that other exceptions are still wrapped in RuntimeError
    def other_exception_input(_: str) -> str:
        raise ValueError("Some other error")

    agent3 = UserProxyAgent(name="test_user", input_func=other_exception_input)
    
    with pytest.raises(RuntimeError) as exc_info:
        await agent3.on_messages(messages, CancellationToken())
    assert "Failed to get user input" in str(exc_info.value)
