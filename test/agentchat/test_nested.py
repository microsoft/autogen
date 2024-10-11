#!/usr/bin/env python3 -m pytest

import os
import sys
from typing import List

import pytest

import autogen
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import reason, skip_openai  # noqa: E402
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402


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


@pytest.mark.skipif(skip_openai, reason=reason)
def test_nested():
    config_list = autogen.config_list_from_json(env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC)
    config_list_35 = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-3.5-turbo"]},
    )
    llm_config = {"config_list": config_list}

    tasks = [
        """What's the date today?""",
        """Make a pleasant joke about it.""",
    ]

    inner_assistant = autogen.AssistantAgent(
        "Inner-assistant",
        llm_config=llm_config,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    inner_code_interpreter = autogen.UserProxyAgent(
        "Inner-code-interpreter",
        human_input_mode="NEVER",
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
        default_auto_reply="",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    groupchat = autogen.GroupChat(
        agents=[inner_assistant, inner_code_interpreter],
        messages=[],
        speaker_selection_method="round_robin",  # With two agents, this is equivalent to a 1:1 conversation.
        allow_repeat_speaker=False,
        max_round=8,
    )

    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
    )

    assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config=False,
        # is_termination_msg=lambda x: x.get("content", "") == "",
    )

    assistant_2 = autogen.AssistantAgent(
        name="Assistant",
        llm_config={"config_list": config_list_35},
        # is_termination_msg=lambda x: x.get("content", "") == "",
    )

    user = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    user_2 = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    writer = autogen.AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list_35},
        system_message="""
        You are a professional writer, known for
        your insightful and engaging articles.
        You transform complex concepts into compelling narratives.
        Reply "TERMINATE" in the end when everything is done.
        """,
    )

    autogen.AssistantAgent(
        name="Reviewer",
        llm_config={"config_list": config_list_35},
        system_message="""
        You are a compliance reviewer, known for your thoroughness and commitment to standards.
        Your task is to scrutinize content for any harmful elements or regulatory violations, ensuring
        all materials align with required guidelines.
        You must review carefully, identify potential issues, and maintain the integrity of the organization.
        Your role demands fairness, a deep understanding of regulations, and a focus on protecting against
        harm while upholding a culture of responsibility.
        You also help make revisions to ensure the content is accurate, clear, and compliant.
        Reply "TERMINATE" in the end when everything is done.
        """,
    )

    def writing_message(recipient, messages, sender, config):
        return f"Make a one-sentence comment. \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}"

    nested_chat_queue = [
        {"sender": user_2, "recipient": manager, "summary_method": "reflection_with_llm"},
        {"recipient": writer, "message": writing_message, "summary_method": "last_msg", "max_turns": 1},
    ]
    assistant.register_nested_chats(
        nested_chat_queue,
        trigger=user,
    )
    user.initiate_chats(
        [
            {"recipient": assistant, "message": tasks[0], "max_turns": 1},
            {"recipient": assistant_2, "message": tasks[1], "max_turns": 1},
        ]
    )


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
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(
        inner_assistant_2
    )

    assistant = autogen.AssistantAgent(
        "Assistant",
    )
    user = autogen.UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        is_termination_msg=is_termination,
    )
    assistant.register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg"}], trigger=user
    )
    chat_result = user.initiate_chat(assistant, message="Start chat")
    assert len(chat_result.chat_history) == 2
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert chat_messages == ["Start chat", "FINAL_RESULT"]


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
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(
        inner_assistant_2
    )

    assistant = autogen.AssistantAgent(
        "Assistant",
    )
    user = autogen.UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        is_termination_msg=is_termination,
    )
    assistant.register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg", "chat_id": 1}],
        trigger=user,
        use_async=True,
    )
    chat_result = await user.a_initiate_chat(assistant, message="Start chat")
    assert len(chat_result.chat_history) == 2
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert chat_messages == ["Start chat", "FINAL_RESULT"]


@pytest.mark.asyncio
async def test_async_nested_chat_chat_id_validation():
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
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(
        inner_assistant_2
    )

    assistant = autogen.AssistantAgent(
        "Assistant",
    )
    user = autogen.UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        is_termination_msg=is_termination,
    )
    with pytest.raises(ValueError, match="chat_id is required for async nested chats"):
        assistant.register_nested_chats(
            [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg"}],
            trigger=user,
            use_async=True,
        )


def test_sync_nested_chat_in_group():
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
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(
        inner_assistant_2
    )

    assistant = autogen.AssistantAgent(
        "Assistant_In_Group_1",
    )
    MockAgentReplies(["Assistant_In_Group_1 message 1"]).add_to_agent(assistant)
    assistant2 = autogen.AssistantAgent(
        "Assistant_In_Group_2",
    )
    user = autogen.UserProxyAgent("User", human_input_mode="NEVER", is_termination_msg=is_termination)
    group = autogen.GroupChat(
        agents=[assistant, assistant2, user],
        messages=[],
        speaker_selection_method="round_robin",
    )
    group_manager = autogen.GroupChatManager(groupchat=group)
    assistant2.register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg"}],
        trigger=group_manager,
    )

    chat_result = user.initiate_chat(group_manager, message="Start chat", summary_method="last_msg")
    assert len(chat_result.chat_history) == 3
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert chat_messages == ["Start chat", "Assistant_In_Group_1 message 1", "FINAL_RESULT"]


@pytest.mark.asyncio
async def test_async_nested_chat_in_group():
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
    MockAgentReplies(["Inner-assistant-2 message 1", "Inner-assistant-2 message 2", "FINAL_RESULT"]).add_to_agent(
        inner_assistant_2
    )

    assistant = autogen.AssistantAgent(
        "Assistant_In_Group_1",
    )
    MockAgentReplies(["Assistant_In_Group_1 message 1"]).add_to_agent(assistant)
    assistant2 = autogen.AssistantAgent(
        "Assistant_In_Group_2",
    )
    user = autogen.UserProxyAgent("User", human_input_mode="NEVER", is_termination_msg=is_termination)
    group = autogen.GroupChat(
        agents=[assistant, assistant2, user],
        messages=[],
        speaker_selection_method="round_robin",
    )
    group_manager = autogen.GroupChatManager(groupchat=group)
    assistant2.register_nested_chats(
        [{"sender": inner_assistant, "recipient": inner_assistant_2, "summary_method": "last_msg", "chat_id": 1}],
        trigger=group_manager,
        use_async=True,
    )

    chat_result = await user.a_initiate_chat(group_manager, message="Start chat", summary_method="last_msg")
    assert len(chat_result.chat_history) == 3
    chat_messages = [msg["content"] for msg in chat_result.chat_history]
    assert chat_messages == ["Start chat", "Assistant_In_Group_1 message 1", "FINAL_RESULT"]


if __name__ == "__main__":
    test_nested()
