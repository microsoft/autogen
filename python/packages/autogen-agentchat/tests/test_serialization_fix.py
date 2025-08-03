"""
Test for the structured logging serialization fix.

This test ensures that BaseModel classes with BaseChatMessage or BaseAgentEvent fields
preserve subclass-specific data during JSON serialization using SerializeAsAny annotations.
"""
import json
from datetime import datetime, timezone
from typing import List, Sequence

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage, CodeGenerationEvent
from autogen_agentchat.teams._group_chat._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatStart,
    GroupChatTeamResponse,
)


def test_group_chat_message_preserves_subclass_data():
    """Test that GroupChatMessage preserves TextMessage subclass fields."""
    # Create a TextMessage with subclass-specific fields
    text_msg = TextMessage(
        content="Hello, world!",
        source="TestAgent",
    )
    
    # Wrap in GroupChatMessage
    group_msg = GroupChatMessage(message=text_msg)
    
    # Serialize and verify subclass fields are preserved
    json_data = group_msg.model_dump_json()
    parsed = json.loads(json_data)
    
    # The critical test: subclass fields should be preserved
    assert "content" in parsed["message"], "TextMessage content field should be preserved"
    assert "type" in parsed["message"], "TextMessage type field should be preserved"
    assert parsed["message"]["content"] == "Hello, world!"
    assert parsed["message"]["type"] == "TextMessage"


def test_group_chat_start_preserves_message_list_data():
    """Test that GroupChatStart preserves subclass data in message lists."""
    text_msg1 = TextMessage(content="First message", source="Agent1")
    text_msg2 = TextMessage(content="Second message", source="Agent2")
    
    group_start = GroupChatStart(messages=[text_msg1, text_msg2])
    
    json_data = group_start.model_dump_json()
    parsed = json.loads(json_data)
    
    # Check both messages preserve subclass data
    assert "content" in parsed["messages"][0]
    assert "content" in parsed["messages"][1]
    assert parsed["messages"][0]["content"] == "First message"
    assert parsed["messages"][1]["content"] == "Second message"


def test_task_result_preserves_mixed_message_types():
    """Test that TaskResult preserves data for mixed BaseAgentEvent and BaseChatMessage types."""
    text_msg = TextMessage(content="Chat message", source="ChatAgent")
    event_msg = CodeGenerationEvent(
        content="Generated code",
        source="CodeAgent",
        retry_attempt=0,
        code_blocks=[]
    )
    
    task_result = TaskResult(messages=[text_msg, event_msg])
    
    json_data = task_result.model_dump_json()
    parsed = json.loads(json_data)
    
    # Verify mixed types preserve their specific fields
    assert "content" in parsed["messages"][0]  # TextMessage
    assert "retry_attempt" in parsed["messages"][1]  # CodeGenerationEvent
    assert "code_blocks" in parsed["messages"][1]  # CodeGenerationEvent
    assert parsed["messages"][0]["content"] == "Chat message"
    assert parsed["messages"][1]["retry_attempt"] == 0


def test_group_chat_agent_response_preserves_dataclass_fields():
    """Test that GroupChatAgentResponse preserves data in Response dataclass fields."""
    text_msg = TextMessage(content="Response message", source="ResponseAgent")
    response = Response(chat_message=text_msg, inner_messages=[])
    
    group_response = GroupChatAgentResponse(response=response, name="TestAgent")
    
    json_data = group_response.model_dump_json()
    parsed = json.loads(json_data)
    
    # Verify dataclass field preserves subclass data
    assert "content" in parsed["response"]["chat_message"]
    assert "type" in parsed["response"]["chat_message"]
    assert parsed["response"]["chat_message"]["content"] == "Response message"


def test_group_chat_team_response_preserves_nested_data():
    """Test that GroupChatTeamResponse preserves deeply nested subclass data."""
    text_msg = TextMessage(content="Nested message", source="NestedAgent")
    task_result = TaskResult(messages=[text_msg])
    
    team_response = GroupChatTeamResponse(result=task_result, name="TestTeam")
    
    json_data = team_response.model_dump_json()
    parsed = json.loads(json_data)
    
    # Verify deeply nested subclass data is preserved
    assert "content" in parsed["result"]["messages"][0]
    assert parsed["result"]["messages"][0]["content"] == "Nested message"


def test_serialization_without_serializeasany_loses_data():
    """Test that demonstrates the issue without SerializeAsAny (for reference)."""
    from pydantic import BaseModel
    
    # Create a class without SerializeAsAny annotation
    class ProblematicGroupChatMessage(BaseModel):
        message: BaseChatMessage  # Missing SerializeAsAny
    
    text_msg = TextMessage(content="This content will be lost", source="TestAgent")
    problematic_msg = ProblematicGroupChatMessage(message=text_msg)
    
    json_data = problematic_msg.model_dump_json()
    parsed = json.loads(json_data)
    
    # Demonstrate the issue: subclass fields are lost
    assert "content" not in parsed["message"], "Without SerializeAsAny, content is lost"
    assert "type" not in parsed["message"], "Without SerializeAsAny, type is lost"


if __name__ == "__main__":
    # Run tests directly if this file is executed
    test_group_chat_message_preserves_subclass_data()
    test_group_chat_start_preserves_message_list_data()
    test_task_result_preserves_mixed_message_types()
    test_group_chat_agent_response_preserves_dataclass_fields()
    test_group_chat_team_response_preserves_nested_data()
    test_serialization_without_serializeasany_loses_data()
    print("✅ All serialization fix tests passed!")