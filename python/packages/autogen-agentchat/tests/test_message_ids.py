import uuid
import json
from datetime import datetime, timezone
from autogen_agentchat.messages import TextMessage, ModelClientStreamingChunkEvent, MessageFactory
from pydantic import ValidationError
import pytest

def test_message_id_generation():
    # Test that a message gets a unique ID on creation
    msg1 = TextMessage(content="Hello", source="user")
    msg2 = TextMessage(content="World", source="user")
    
    assert isinstance(msg1.id, str)
    assert len(msg1.id) > 0
    assert msg1.id != msg2.id
    # Verify it's a valid UUID
    uuid.UUID(msg1.id)

def test_serialization_deserialization():
    # Test that ID is preserved during serialization/deserialization
    msg = TextMessage(content="Hello", source="user")
    original_id = msg.id
    
    # Dump to dict
    data = msg.dump()
    assert data["id"] == original_id
    
    # Load from dict
    factory = MessageFactory()
    loaded_msg = factory.create(data)
    
    assert isinstance(loaded_msg, TextMessage)
    assert loaded_msg.id == original_id
    assert loaded_msg.content == "Hello"

def test_backwards_compatibility():
    # Test that loading a message without an ID generates one
    data = {
        "type": "TextMessage",
        "content": "Old message",
        "source": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {},
        "models_usage": None
    }
    
    factory = MessageFactory()
    loaded_msg = factory.create(data)
    
    assert isinstance(loaded_msg.id, str)
    assert len(loaded_msg.id) > 0
    # Verify it's a valid UUID
    uuid.UUID(loaded_msg.id)

def test_streaming_correlation_id():
    # Test that ModelClientStreamingChunkEvent can hold a correlation ID
    message_id = str(uuid.uuid4())
    chunk = ModelClientStreamingChunkEvent(
        content="Hello",
        source="assistant",
        full_message_id=message_id
    )
    
    assert chunk.full_message_id == message_id
    
    # Verify serialization
    data = chunk.dump()
    assert data["full_message_id"] == message_id
    
    factory = MessageFactory()
    loaded_chunk = factory.create(data)
    assert loaded_chunk.full_message_id == message_id

if __name__ == "__main__":
    # Run tests manually if not using pytest
    test_message_id_generation()
    test_serialization_deserialization()
    test_backwards_compatibility()
    test_streaming_correlation_id()
    print("All tests passed!")
