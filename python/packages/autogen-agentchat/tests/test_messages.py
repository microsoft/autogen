from autogen_agentchat.messages import StructuredMessage
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
    assert message.type == "StructuredMessage"

    # Check that the content is of the correct type
    assert isinstance(message.content, TestContent)

    # Check that the content class is set correctly
    assert message.content_class_path == "test_messages.TestContent"

    # Check that the content fields are set correctly
    assert message.content.field1 == "test"
    assert message.content.field2 == 42

    # Check that model_dump works correctly
    dumped_message = message.model_dump()
    assert dumped_message["source"] == "test_agent"
    assert dumped_message["content_class_path"] == "test_messages.TestContent"
    assert dumped_message["content"]["field1"] == "test"
    assert dumped_message["content"]["field2"] == 42

    # Check that model_validate works correctly
    validated_message = StructuredMessage[TestContent].model_validate(dumped_message)
    assert validated_message.source == "test_agent"
    assert isinstance(validated_message.content, TestContent)
    assert validated_message.content_class_path == "test_messages.TestContent"
    assert validated_message.content.field1 == "test"
    assert validated_message.content.field2 == 42

    # Check that the dump method works correctly
    dumped_message = message.dump()
    assert dumped_message["type"] == "StructuredMessage"
    assert dumped_message["content_class_path"] == "test_messages.TestContent"
    assert dumped_message["content"]["field1"] == "test"
    assert dumped_message["content"]["field2"] == 42

    # Check that the load method works correctly for dynamic deserialization.
    message2 = StructuredMessage[BaseModel].load(dumped_message)
    assert message2.type == "StructuredMessage"
    assert isinstance(message2.content, TestContent)
    assert message2.content_class_path == "test_messages.TestContent"
    assert message2.content.field1 == "test"
    assert message2.content.field2 == 42
