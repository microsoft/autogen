import json

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import CodeGenerationEvent, TextMessage
from autogen_agentchat.teams._group_chat._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatStart,
    GroupChatTeamResponse,
)


def test_group_chat_message_preserves_subclass_data() -> None:
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


def test_group_chat_start_preserves_message_list_data() -> None:
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


def test_group_chat_agent_response_preserves_dataclass_fields() -> None:
    """Test that GroupChatAgentResponse preserves data in Response dataclass fields."""
    text_msg = TextMessage(content="Response message", source="ResponseAgent")
    inner_text_msg = TextMessage(content="Inner message", source="InnerAgent")
    response = Response(chat_message=text_msg, inner_messages=[inner_text_msg])

    group_response = GroupChatAgentResponse(response=response, name="TestAgent")

    json_data = group_response.model_dump_json()
    parsed = json.loads(json_data)

    # Verify dataclass field preserves subclass data
    assert "content" in parsed["response"]["chat_message"]
    assert "type" in parsed["response"]["chat_message"]
    assert parsed["response"]["chat_message"]["content"] == "Response message"
    inner_msgs = parsed["response"]["inner_messages"]
    assert len(inner_msgs) == 1
    assert "content" in inner_msgs[0]
    assert inner_msgs[0]["content"] == "Inner message"


def test_group_chat_team_response_preserves_nested_data() -> None:
    """Test that GroupChatTeamResponse preserves deeply nested subclass data."""
    text_msg = TextMessage(content="Nested message", source="NestedAgent")
    task_result = TaskResult(messages=[text_msg])

    team_response = GroupChatTeamResponse(result=task_result, name="TestTeam")

    json_data = team_response.model_dump_json()
    parsed = json.loads(json_data)

    # Verify deeply nested subclass data is preserved
    assert "content" in parsed["result"]["messages"][0]
    assert parsed["result"]["messages"][0]["content"] == "Nested message"
