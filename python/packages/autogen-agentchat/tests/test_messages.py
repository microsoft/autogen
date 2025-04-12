import json
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
    StructuredMessageComponent,
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
    # Create a structured message with the test contentformat_string="this is a string {field1} and this is an int {field2}"
    format_string="this is a string {field1} and this is an int {field2}"
    s_m = StructuredMessageComponent(input_model=TestContent, format_string=format_string)
    config = s_m._to_config()
    s_m_dyn = StructuredMessageComponent._from_config(config)
    message = s_m_dyn.StructuredMessage(source="test_agent", content=s_m_dyn.ContentModel(field1="test", field2=42), format_string=s_m_dyn.format_string)

    assert isinstance(message.content, s_m_dyn.ContentModel)
    assert not isinstance(message.content, TestContent)
    assert message.content.field1 == "test"
    assert message.content.field2 == 42

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
