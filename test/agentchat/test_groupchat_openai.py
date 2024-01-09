import autogen
import pytest
import sys
import os
from io import StringIO
import logging
from unittest.mock import MagicMock
import unittest
from autogen.agentchat.groupchat import Agent, ConversableAgent
from autogen.agentchat.assistant_agent import AssistantAgent

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

config_list = autogen.config_list_from_json(
    OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"api_type": ["openai"]}
)

config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, filter_dict={"model": ["dev-oai-gpt4"]})
llm_config = {"config_list": config_list, "cache_seed": 100}

def test_recursion_error():
        
        # Mock Agents
        agent1 = autogen.AssistantAgent(name="alice", llm_config=llm_config)

        # Termination message detection
        def is_termination_msg(content) -> bool:
            have_content = content.get("content", None) is not None
            if have_content and "TERMINATE" in content["content"]:
                return True
            return False

        # Terminates the conversation when TERMINATE is detected.
        user_proxy = autogen.UserProxyAgent(
            name="User_proxy",
            system_message="Terminator admin.",
            code_execution_config=False,
            is_termination_msg=is_termination_msg,
            human_input_mode="NEVER",
        )

        agents = [agent1, user_proxy]

        group_chat = autogen.GroupChat(
            agents=agents, 
            messages=[], 
            max_round=20
        )

        # Create the manager
        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=llm_config)

        # Initiates the chat with Alice
        agents[0].initiate_chat(
            manager,
            message="""Ask alice what is the largest single digit prime number.""",
        )

        # Assert the messages contain 7
        # don't just check the last message
        assert any("7" in message["content"] for message in group_chat.messages)

        # Assert the messages contain alice
        assert any("alice" in message["name"] for message in group_chat.messages)
