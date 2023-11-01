import unittest
from unittest.mock import MagicMock

from autogen.agentchat import Agent, MultimodalConversableAgent

base64_encoded_image = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)


class TestMultimodalConversableAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MultimodalConversableAgent(name="TestAgent")

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
