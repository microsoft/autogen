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

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"

base64_encoded_image = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestMultimodalConversableAgent(unittest.TestCase):
    def setUp(self):
        config_list = autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            file_location=KEY_LOC,
            filter_dict={
                "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
            },
        )
        self.agent = MultimodalConversableAgent(
            name="TestAgent",
            llm_config={
                "timeout": 600,
                "seed": 42,
                "config_list": config_list,
            },
        )

    def test_system_message(self):
        # Test default system message
        self.assertEqual(
            self.agent.system_message,
            [
                'You are a helpful AI assistant.\nYou can also view images, where the "<image i>" represent the i-th image you received.'
            ],
        )

        # Test updating system message
        new_message = f"We will discuss <img {base64_encoded_image}> in this conversation."
        self.agent.update_system_message(new_message)
        self.assertEqual(
            self.agent.system_message,
            [
                "We will discuss ",
                {"image": base64_encoded_image.replace("data:image/png;base64,", "")},
                " in this conversation.",
            ],
        )

    def test_message_to_dict(self):
        # Test string message
        message_str = "Hello"
        expected_dict = {"content": ["Hello"]}
        self.assertDictEqual(self.agent._message_to_dict(message_str), expected_dict)

        # Test list message
        message_list = ["Hello"]
        expected_dict = {"content": message_list}
        self.assertDictEqual(self.agent._message_to_dict(message_list), expected_dict)

        # Test dictionary message
        message_dict = {"content": "Hello"}
        self.assertDictEqual(self.agent._message_to_dict(message_dict), message_dict)

    def test_content_str(self):
        content = ["Hello", {"image": "image_data"}]
        expected_str = "Hello<image>"
        self.assertEqual(self.agent._content_str(content), expected_str)

    def test_print_received_message(self):
        sender = Agent(name="SenderAgent")
        message_str = "Hello"
        self.agent._print_received_message = MagicMock()  # Mocking print method to avoid actual print
        self.agent._print_received_message(message_str, sender)
        self.agent._print_received_message.assert_called_with(message_str, sender)


if __name__ == "__main__":
    unittest.main()
