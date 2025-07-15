import json
import uuid
from datetime import datetime, timezone
from typing import List

import pytest
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    HandoffMessage,
    MessageFactory,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StopMessage,
    StructuredMessage,
    StructuredMessageFactory,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_core import FunctionCall
from autogen_core.models import FunctionExecutionResult
from pydantic import BaseModel


class TestContent(BaseModel):
    """Test content model."""

    field1: str
    field2: int


def test_structured_message() -> None:
    # Create a structured message with the test content
    message = StructuredMessage[TestContent](
        source="test_agent",
        content=TestContent(field1="test", field2=42),
    )

    # Check that the message type is correct
    assert message.type == "StructuredMessage[TestContent]"  # type: ignore[comparison-overlap]

    # Check that the content is of the correct type
    assert isinstance(message.content, TestContent)

    # Check that the content fields are set correctly
    assert message.content.field1 == "test"
    assert message.content.field2 == 42

    # Check that model_dump works correctly
    dumped_message = message.model_dump()
    assert dumped_message["source"] == "test_agent"
    assert dumped_message["content"]["field1"] == "test"
    assert dumped_message["content"]["field2"] == 42
    assert dumped_message["type"] == "StructuredMessage[TestContent]"


def test_structured_message_component() -> None:
    # Create a structured message with the test content
    format_string = "this is a string {field1} and this is an int {field2}"
    s_m = StructuredMessageFactory(input_model=TestContent, format_string=format_string)
    config = s_m.dump_component()
    s_m_dyn = StructuredMessageFactory.load_component(config)
    message = s_m_dyn.StructuredMessage(
        source="test_agent", content=s_m_dyn.ContentModel(field1="test", field2=42), format_string=s_m_dyn.format_string
    )

    assert isinstance(message.content, s_m_dyn.ContentModel)
    assert not isinstance(message.content, TestContent)
    assert message.content.field1 == "test"  # type: ignore[attr-defined]
    assert message.content.field2 == 42  # type: ignore[attr-defined]

    dumped_message = message.model_dump()
    assert dumped_message["source"] == "test_agent"
    assert dumped_message["content"]["field1"] == "test"
    assert dumped_message["content"]["field2"] == 42
    assert message.to_model_text() == format_string.format(field1="test", field2=42)


def test_message_factory() -> None:
    factory = MessageFactory()

    # Text message data
    text_data = {
        "type": "TextMessage",
        "source": "test_agent",
        "content": "Hello, world!",
    }

    # Create a TextMessage instance
    text_message = factory.create(text_data)
    assert isinstance(text_message, TextMessage)
    assert text_message.source == "test_agent"
    assert text_message.content == "Hello, world!"
    assert text_message.type == "TextMessage"  # type: ignore[comparison-overlap]

    # Handoff message data
    handoff_data = {
        "type": "HandoffMessage",
        "source": "test_agent",
        "content": "handoff to another agent",
        "target": "target_agent",
    }

    # Create a HandoffMessage instance
    handoff_message = factory.create(handoff_data)
    assert isinstance(handoff_message, HandoffMessage)
    assert handoff_message.source == "test_agent"
    assert handoff_message.content == "handoff to another agent"
    assert handoff_message.target == "target_agent"
    assert handoff_message.type == "HandoffMessage"  # type: ignore[comparison-overlap]

    # Structured message data
    structured_data = {
        "type": "StructuredMessage[TestContent]",
        "source": "test_agent",
        "content": {
            "field1": "test",
            "field2": 42,
        },
    }
    # Create a StructuredMessage instance -- this will fail because the type
    # is not registered in the factory.
    with pytest.raises(ValueError):
        structured_message = factory.create(structured_data)
    # Register the StructuredMessage type in the factory
    factory.register(StructuredMessage[TestContent])
    # Create a StructuredMessage instance
    structured_message = factory.create(structured_data)
    assert isinstance(structured_message, StructuredMessage)
    assert isinstance(structured_message.content, TestContent)  # type: ignore[reportUnkownMemberType]
    assert structured_message.source == "test_agent"
    assert structured_message.content.field1 == "test"
    assert structured_message.content.field2 == 42
    assert structured_message.type == "StructuredMessage[TestContent]"  # type: ignore[comparison-overlap]

    sm_factory = StructuredMessageFactory(input_model=TestContent, format_string=None, content_model_name="TestContent")
    config = sm_factory.dump_component()
    config.config["content_model_name"] = "DynamicTestContent"
    sm_factory_dynamic = StructuredMessageFactory.load_component(config)

    factory.register(sm_factory_dynamic.StructuredMessage)
    msg = sm_factory_dynamic.StructuredMessage(
        content=sm_factory_dynamic.ContentModel(field1="static", field2=123), source="static_agent"
    )
    restored = factory.create(msg.dump())
    assert isinstance(restored, StructuredMessage)
    assert isinstance(restored.content, sm_factory_dynamic.ContentModel)  # type: ignore[reportUnkownMemberType]
    assert restored.source == "static_agent"
    assert restored.content.field1 == "static"  # type: ignore[attr-defined]
    assert restored.content.field2 == 123  # type: ignore[attr-defined]


class TestContainer(BaseModel):
    chat_messages: List[ChatMessage]
    agent_events: List[AgentEvent]


def test_union_types() -> None:
    # Create a few messages.
    chat_messages: List[ChatMessage] = [
        TextMessage(source="user", content="Hello!"),
        MultiModalMessage(source="user", content=["Hello!", "World!"]),
        HandoffMessage(source="user", content="handoff to another agent", target="target_agent"),
        StopMessage(source="user", content="stop"),
    ]

    # Create a few agent events.
    agent_events: List[AgentEvent] = [
        ModelClientStreamingChunkEvent(source="user", content="Hello!"),
        ToolCallRequestEvent(
            content=[
                FunctionCall(id="1", name="test_function", arguments=json.dumps({"arg1": "value1", "arg2": "value2"}))
            ],
            source="user",
        ),
        ToolCallExecutionEvent(
            content=[FunctionExecutionResult(call_id="1", content="result", name="test")], source="user"
        ),
    ]

    # Create a container with the messages.
    container = TestContainer(chat_messages=chat_messages, agent_events=agent_events)

    # Dump the container to JSON.
    data = container.model_dump()

    # Load the container from JSON.
    loaded_container = TestContainer.model_validate(data)
    assert loaded_container.chat_messages == chat_messages
    assert loaded_container.agent_events == agent_events


def test_message_id_field() -> None:
    """Test that messages have unique ID fields automatically generated."""
    # Test BaseChatMessage subclass (TextMessage)
    message1 = TextMessage(source="test_agent", content="Hello, world!")
    message2 = TextMessage(source="test_agent", content="Hello, world!")

    # Check that IDs are present and unique
    assert hasattr(message1, "id")
    assert hasattr(message2, "id")
    assert message1.id != message2.id
    assert isinstance(message1.id, str)
    assert isinstance(message2.id, str)

    # Check that IDs are valid UUIDs
    try:
        uuid.UUID(message1.id)
        uuid.UUID(message2.id)
    except ValueError:
        pytest.fail("Generated IDs are not valid UUIDs")

    # Test BaseAgentEvent subclass (ModelClientStreamingChunkEvent)
    event1 = ModelClientStreamingChunkEvent(source="test_agent", content="chunk1")
    event2 = ModelClientStreamingChunkEvent(source="test_agent", content="chunk2")

    # Check that IDs are present and unique
    assert hasattr(event1, "id")
    assert hasattr(event2, "id")
    assert event1.id != event2.id
    assert isinstance(event1.id, str)
    assert isinstance(event2.id, str)

    # Check that IDs are valid UUIDs
    try:
        uuid.UUID(event1.id)
        uuid.UUID(event2.id)
    except ValueError:
        pytest.fail("Generated IDs are not valid UUIDs")


def test_custom_message_id() -> None:
    """Test that custom IDs can be provided."""
    custom_id = "custom-message-id-123"
    message = TextMessage(id=custom_id, source="test_agent", content="Hello, world!")

    assert message.id == custom_id

    custom_event_id = "custom-event-id-456"
    event = ModelClientStreamingChunkEvent(id=custom_event_id, source="test_agent", content="chunk")

    assert event.id == custom_event_id


def test_streaming_chunk_full_message_id() -> None:
    """Test the full_message_id field in ModelClientStreamingChunkEvent."""
    # Test without full_message_id
    chunk1 = ModelClientStreamingChunkEvent(source="test_agent", content="chunk1")
    assert chunk1.full_message_id is None

    # Test with full_message_id
    full_msg_id = "full-message-123"
    chunk2 = ModelClientStreamingChunkEvent(source="test_agent", content="chunk2", full_message_id=full_msg_id)
    assert chunk2.full_message_id == full_msg_id

    # Test that chunk has its own ID separate from full_message_id
    assert chunk2.id != chunk2.full_message_id
    assert isinstance(chunk2.id, str)

    # Verify chunk ID is a valid UUID
    try:
        uuid.UUID(chunk2.id)
    except ValueError:
        pytest.fail("Chunk ID is not a valid UUID")


def test_message_serialization_with_id() -> None:
    """Test that messages with IDs serialize and deserialize correctly."""
    # Create a message with auto-generated ID
    original_message = TextMessage(source="test_agent", content="Hello, world!")
    original_id = original_message.id

    # Serialize to dict
    message_data = original_message.model_dump()
    assert "id" in message_data
    assert message_data["id"] == original_id

    # Deserialize from dict
    restored_message = TextMessage.model_validate(message_data)
    assert restored_message.id == original_id
    assert restored_message.source == "test_agent"
    assert restored_message.content == "Hello, world!"

    # Test with streaming chunk event
    original_chunk = ModelClientStreamingChunkEvent(
        source="test_agent", content="chunk", full_message_id="full-msg-123"
    )
    original_chunk_id = original_chunk.id

    # Serialize to dict
    chunk_data = original_chunk.model_dump()
    assert "id" in chunk_data
    assert "full_message_id" in chunk_data
    assert chunk_data["id"] == original_chunk_id
    assert chunk_data["full_message_id"] == "full-msg-123"

    # Deserialize from dict
    restored_chunk = ModelClientStreamingChunkEvent.model_validate(chunk_data)
    assert restored_chunk.id == original_chunk_id
    assert restored_chunk.full_message_id == "full-msg-123"
    assert restored_chunk.content == "chunk"


def test_datetime_serialization_in_messages() -> None:
    """Test that datetime objects in messages are properly serialized to JSON-compatible format.
    
    This test validates the fix for issue #6793 where datetime objects in message
    created_at fields caused JSON serialization errors when saving team state.
    """
    # Create a specific datetime for testing
    test_datetime = datetime(2023, 12, 25, 10, 30, 45, 123456, timezone.utc)
    
    # Test BaseChatMessage subclass with datetime
    chat_message = TextMessage(source="test_agent", content="Hello, world!", created_at=test_datetime)
    
    # Test that dump() returns JSON-serializable data
    chat_message_data = chat_message.dump()
    
    # Verify that the datetime is converted to a string in ISO format
    assert isinstance(chat_message_data["created_at"], str)
    # Pydantic JSON mode converts UTC timezone to 'Z' format instead of '+00:00'
    expected_iso = test_datetime.isoformat().replace('+00:00', 'Z')
    assert chat_message_data["created_at"] == expected_iso
    
    # Verify that the dumped data is JSON serializable
    json_string = json.dumps(chat_message_data)
    assert isinstance(json_string, str)
    
    # Test round-trip serialization (dump -> load)
    restored_chat_message = TextMessage.load(chat_message_data)
    assert restored_chat_message.source == "test_agent"
    assert restored_chat_message.content == "Hello, world!"
    assert restored_chat_message.created_at == test_datetime
    
    # Test BaseAgentEvent subclass with datetime
    agent_event = ModelClientStreamingChunkEvent(
        source="test_agent", 
        content="chunk", 
        created_at=test_datetime
    )
    
    # Test that dump() returns JSON-serializable data
    agent_event_data = agent_event.dump()
    
    # Verify that the datetime is converted to a string in ISO format
    assert isinstance(agent_event_data["created_at"], str)
    assert agent_event_data["created_at"] == expected_iso
    
    # Verify that the dumped data is JSON serializable
    json_string = json.dumps(agent_event_data)
    assert isinstance(json_string, str)
    
    # Test round-trip serialization (dump -> load)
    restored_agent_event = ModelClientStreamingChunkEvent.load(agent_event_data)
    assert restored_agent_event.source == "test_agent"
    assert restored_agent_event.content == "chunk"
    assert restored_agent_event.created_at == test_datetime
    
    # Test with auto-generated datetime (default created_at)
    auto_message = TextMessage(source="test_agent", content="Auto datetime test")
    auto_message_data = auto_message.dump()
    
    # Verify datetime is serialized as string
    assert isinstance(auto_message_data["created_at"], str)
    
    # Verify JSON serialization works without errors
    json.dumps(auto_message_data)
    
    # Test round-trip with auto-generated datetime
    restored_auto_message = TextMessage.load(auto_message_data)
    assert restored_auto_message.created_at == auto_message.created_at
