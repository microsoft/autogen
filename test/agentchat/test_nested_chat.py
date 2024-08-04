import pytest
import autogen
from typing import List
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability

class MockAgentReplies(AgentCapability):
    def __init__(self, mock_messages: List[str]):
        self.mock_messages = mock_messages
        self.mock_message_index = 0

    def add_to_agent(self, agent: autogen.ConversableAgent):
        def mock_reply(recipient, messages, sender, config):
            if self.mock_message_index < len(self.mock_messages):
                reply_msg = self.mock_messages[self.mock_message_index]
                self.mock_message_index += 1
                return [True, reply_msg]
            else:
                raise ValueError(f"No more mock messages available for {sender.name} to reply to {recipient.name}")
        agent.register_reply([autogen.Agent, None], mock_reply, position=2)

def test_sync_nested_chat():
    def is_termination(msg):
        if isinstance(msg, str) and msg == "FINAL_RESULT":
            return True
        elif isinstance(msg, dict) and msg.get("content") == "FINAL_RESULT":
            return True
        return False
    inner_assistant = autogen.AssistantAgent(
        "Inner-assistant",
        is_termination_msg=is_termination,
    )
    MockAgentReplies(["Inner-assistant message 1", "Inner-assistant message 2"]).add_to_agent(inner_assistant)
    
    inner_assistant_2 = autogen.AssistantAgent(
        "Inner-assistant-2",
    )
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(inner_assistant_2)
    
    assistant = autogen.AssistantAgent(
        "Assistant",
    )
    user = autogen.UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        is_termination_msg=is_termination,
        
    )
    assistant.register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg"}],
        trigger=user
    )
    chat_result = user.initiate_chat(assistant, message="Start chat")
    assert(len(chat_result.chat_history) == 2)
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert(chat_messages == ["Start chat", "FINAL_RESULT"])
    
@pytest.mark.asyncio
async def test_async_nested_chat():
    def is_termination(msg):
        if isinstance(msg, str) and msg == "FINAL_RESULT":
            return True
        elif isinstance(msg, dict) and msg.get("content") == "FINAL_RESULT":
            return True
        return False
    inner_assistant = autogen.AssistantAgent(
        "Inner-assistant",
        is_termination_msg=is_termination,
    )
    MockAgentReplies(["Inner-assistant message 1", "Inner-assistant message 2"]).add_to_agent(inner_assistant)
    
    inner_assistant_2 = autogen.AssistantAgent(
        "Inner-assistant-2",
    )
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(inner_assistant_2)
    
    assistant = autogen.AssistantAgent(
        "Assistant",
    )
    user = autogen.UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        is_termination_msg=is_termination,
        
    )
    assistant.a_register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg", "chat_id": 1}],
        trigger=user
    )
    chat_result = await user.a_initiate_chat(assistant, message="Start chat")
    assert(len(chat_result.chat_history) == 2)
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert(chat_messages == ["Start chat", "FINAL_RESULT"])

def test_sync_nested_chat_in_group():
    pass

def test_async_nested_chat_in_group():
    pass

if __name__ == "__main__":
    test_sync_nested_chat()