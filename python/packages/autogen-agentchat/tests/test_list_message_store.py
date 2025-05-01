import asyncio
from typing import List, cast

import pytest
from autogen_agentchat.message_store._list_message_store import ListMessageStore
from autogen_agentchat.messages import MessageFactory, TextMessage, ToolCallRequestEvent
from autogen_core import FunctionCall


@pytest.mark.asyncio
async def test_add_get_single_message() -> None:
    """Test adding and retrieving a single message."""
    store = ListMessageStore(MessageFactory())
    message = TextMessage(source="test_agent", content="Hello, world!")
    await store.add_message(message)

    # Retrieve messages and verify
    messages = cast(List[TextMessage], await store.get_messages())
    assert len(messages) == 1
    assert messages[0].source == "test_agent"
    assert messages[0].content == "Hello, world!"
    assert isinstance(messages[0], TextMessage)


@pytest.mark.asyncio
async def test_add_get_multiple_messages() -> None:
    """Test adding and retrieving multiple messages."""
    store = ListMessageStore(MessageFactory())
    messages = [
        TextMessage(source="agent1", content="Message 1"),
        TextMessage(source="agent2", content="Message 2"),
        TextMessage(source="agent1", content="Message 3"),
    ]
    await store.add_messages(messages)

    # Retrieve messages and verify
    stored_messages = cast(List[TextMessage], await store.get_messages())
    assert len(stored_messages) == 3
    assert stored_messages[0].source == "agent1"
    assert stored_messages[0].content == "Message 1"
    assert stored_messages[1].source == "agent2"
    assert stored_messages[1].content == "Message 2"
    assert stored_messages[2].source == "agent1"
    assert stored_messages[2].content == "Message 3"


@pytest.mark.asyncio
async def test_add_messages_empty_list() -> None:
    """Test adding an empty list of messages."""
    store = ListMessageStore(MessageFactory())
    await store.add_messages([])

    # Verify that no messages were added
    messages = await store.get_messages()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_reset_messages_empty() -> None:
    """Test resetting messages to an empty state."""
    store = ListMessageStore(MessageFactory())
    messages = [
        TextMessage(source="agent1", content="Message 1"),
        TextMessage(source="agent2", content="Message 2"),
    ]
    await store.add_messages(messages)

    # Verify messages were added
    stored_messages = await store.get_messages()
    assert len(stored_messages) == 2

    # Reset messages
    await store.reset_messages()

    # Verify messages were cleared
    stored_messages = await store.get_messages()
    assert len(stored_messages) == 0


@pytest.mark.asyncio
async def test_reset_messages_with_new_messages() -> None:
    """Test resetting messages with new messages."""
    store = ListMessageStore(MessageFactory())
    initial_messages = [
        TextMessage(source="agent1", content="Initial 1"),
        TextMessage(source="agent2", content="Initial 2"),
    ]
    await store.add_messages(initial_messages)

    # Reset with new messages
    new_messages = [
        TextMessage(source="agent3", content="New 1"),
        TextMessage(source="agent4", content="New 2"),
        TextMessage(source="agent5", content="New 3"),
    ]
    await store.reset_messages(new_messages)

    # Verify messages were replaced
    stored_messages = cast(List[TextMessage], await store.get_messages())
    assert len(stored_messages) == 3
    assert stored_messages[0].source == "agent3"
    assert stored_messages[0].content == "New 1"
    assert stored_messages[1].source == "agent4"
    assert stored_messages[1].content == "New 2"
    assert stored_messages[2].source == "agent5"
    assert stored_messages[2].content == "New 3"


@pytest.mark.asyncio
async def test_ttl_expired_messages() -> None:
    """Test that messages expire after TTL period."""
    # Create store with 2 second TTL
    store = ListMessageStore(MessageFactory(), ttl_sec=2)

    # Add a message
    message = TextMessage(source="agent1", content="This will expire")
    await store.add_message(message)

    # Verify message was added
    messages = await store.get_messages()
    assert len(messages) == 1

    # Wait for TTL to expire
    await asyncio.sleep(2.1)

    # Verify message was removed due to TTL
    messages = await store.get_messages()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_ttl_mixed_expiration() -> None:
    """Test that only expired messages are removed."""
    # Create store with 2 second TTL
    store = ListMessageStore(MessageFactory(), ttl_sec=2)

    # Add a message that will expire
    message1 = TextMessage(source="agent1", content="This will expire")
    await store.add_message(message1)

    # Wait a bit but not enough to expire
    await asyncio.sleep(1)

    # Add another message
    message2 = TextMessage(source="agent2", content="This will remain")
    await store.add_message(message2)

    # Wait for first message to expire
    await asyncio.sleep(1.1)

    # Verify only the second message remains
    messages = cast(List[TextMessage], await store.get_messages())
    assert len(messages) == 1
    assert messages[0].source == "agent2"
    assert messages[0].content == "This will remain"


@pytest.mark.asyncio
async def test_no_ttl() -> None:
    """Test that messages don't expire when TTL is None."""
    # Create store with no TTL
    store = ListMessageStore(MessageFactory(), ttl_sec=None)

    # Add a message
    message = TextMessage(source="agent1", content="This will not expire")
    await store.add_message(message)

    # Wait some time
    await asyncio.sleep(1)

    # Verify message still exists
    messages = cast(List[TextMessage], await store.get_messages())
    assert len(messages) == 1
    assert messages[0].source == "agent1"
    assert messages[0].content == "This will not expire"


@pytest.mark.asyncio
async def test_different_message_types() -> None:
    """Test storing different message types."""
    store = ListMessageStore(MessageFactory())

    # Create messages of different types
    text_message = TextMessage(source="agent1", content="Text message")
    event_message = ToolCallRequestEvent(
        source="agent2", content=[FunctionCall(id="123", name="test_function", arguments='{"arg1": "value1"}')]
    )

    # Add messages
    await store.add_message(text_message)
    await store.add_message(event_message)

    # Verify both messages were stored correctly
    messages = cast(List[TextMessage | ToolCallRequestEvent], await store.get_messages())
    assert len(messages) == 2

    # Check types and content of messages
    assert isinstance(messages[0], TextMessage)
    assert messages[0].source == "agent1"
    assert messages[0].content == "Text message"

    assert isinstance(messages[1], ToolCallRequestEvent)
    assert messages[1].source == "agent2"
    assert len(messages[1].content) == 1
    assert messages[1].content[0].name == "test_function"
    assert messages[1].content[0].id == "123"


@pytest.mark.asyncio
async def test_concurrent_operations() -> None:
    """Test concurrent operations on the message store."""
    store = ListMessageStore(MessageFactory())

    # Create multiple concurrent tasks
    async def add_messages(prefix: str, count: int) -> None:
        for i in range(count):
            await store.add_message(TextMessage(source=f"agent-{prefix}", content=f"Message {prefix}-{i}"))

    # Run concurrent operations
    await asyncio.gather(add_messages("A", 5), add_messages("B", 5), add_messages("C", 5))

    # Verify all messages were added
    messages = await store.get_messages()
    assert len(messages) == 15

    # Check that we have the expected number of messages from each source
    sources = [msg.source for msg in messages]
    assert sources.count("agent-A") == 5
    assert sources.count("agent-B") == 5
    assert sources.count("agent-C") == 5
