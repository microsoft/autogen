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


if __name__ == "__main__":
    unittest.main()
