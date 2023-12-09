import unittest
from unittest.mock import MagicMock

import pytest

import autogen
from autogen.agentchat.agent import Agent

try:
    from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
except ImportError:
    skip = True
else:
    skip = False


base64_encoded_image = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestMultimodalConversableAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MultimodalConversableAgent(
            name="TestAgent",
            llm_config={
                "timeout": 600,
                "seed": 42,
                "config_list": [{"model": "gpt-4-vision-preview", "api_key": "sk-fake"}],
            },
        )

    def test_system_message(self):
        # Test default system message
        self.assertEqual(
            self.agent.system_message,
            [
                {
                    "type": "text",
                    "text": "You are a helpful AI assistant.",
                }
            ],
        )

        # Test updating system message
        new_message = f"We will discuss <img {base64_encoded_image}> in this conversation."
        self.agent.update_system_message(new_message)
        self.assertEqual(
            self.agent.system_message,
            [
                {"type": "text", "text": "We will discuss "},
                {"type": "image_url", "image_url": {"url": base64_encoded_image}},
                {"type": "text", "text": " in this conversation."},
            ],
        )

    def test_message_to_dict(self):
        # Test string message
        message_str = "Hello"
        expected_dict = {"content": [{"type": "text", "text": "Hello"}]}
        self.assertDictEqual(self.agent._message_to_dict(message_str), expected_dict)

        # Test list message
        message_list = [{"type": "text", "text": "Hello"}]
        expected_dict = {"content": message_list}
        self.assertDictEqual(self.agent._message_to_dict(message_list), expected_dict)

        # Test dictionary message
        message_dict = {"content": [{"type": "text", "text": "Hello"}]}
        self.assertDictEqual(self.agent._message_to_dict(message_dict), message_dict)

    def test_print_received_message(self):
        sender = Agent(name="SenderAgent")
        message_str = "Hello"
        self.agent._print_received_message = MagicMock()  # Mocking print method to avoid actual print
        self.agent._print_received_message(message_str, sender)
        self.agent._print_received_message.assert_called_with(message_str, sender)


@pytest.mark.skipif(skip, reason="Dependency not installed")
def test_group_chat_with_lmm():
    """
    Tests the group chat functionality with two MultimodalConversable Agents.
    Verifies that the chat is correctly limited by the max_round parameter.
    Each agent is set to describe an image in a unique style, but the chat should not exceed the specified max_rounds.
    """

    # Configuration parameters
    max_round = 5
    max_consecutive_auto_reply = 10
    llm_config = False

    # Creating two MultimodalConversable Agents with different descriptive styles
    agent1 = MultimodalConversableAgent(
        name="image-explainer-1",
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        llm_config=llm_config,
        system_message="Your image description is poetic and engaging.",
    )
    agent2 = MultimodalConversableAgent(
        name="image-explainer-2",
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        llm_config=llm_config,
        system_message="Your image description is factual and to the point.",
    )

    # Creating a user proxy agent for initiating the group chat
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="Ask both image explainer 1 and 2 for their description.",
        human_input_mode="NEVER",  # Options: 'ALWAYS' or 'NEVER'
        max_consecutive_auto_reply=max_consecutive_auto_reply,
    )

    # Setting up the group chat
    groupchat = autogen.GroupChat(agents=[agent1, agent2, user_proxy], messages=[], max_round=max_round)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    # Initiating the group chat and observing the number of rounds
    user_proxy.initiate_chat(group_chat_manager, message=f"What do you see? <img {base64_encoded_image}>")

    # Assertions to check if the number of rounds does not exceed max_round
    assert all(len(arr) <= max_round for arr in agent1._oai_messages.values()), "Agent 1 exceeded max rounds"
    assert all(len(arr) <= max_round for arr in agent2._oai_messages.values()), "Agent 2 exceeded max rounds"
    assert all(len(arr) <= max_round for arr in user_proxy._oai_messages.values()), "User proxy exceeded max rounds"


if __name__ == "__main__":
    unittest.main()
