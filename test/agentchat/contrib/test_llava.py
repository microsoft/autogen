import unittest
from unittest.mock import MagicMock, patch

import pytest

import autogen

try:
    from autogen.agentchat.contrib.llava_agent import (
        LLaVAAgent,
        _llava_call_binary_with_config,
        llava_call,
        llava_call_binary,
    )
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestLLaVAAgent(unittest.TestCase):
    def setUp(self):
        self.agent = LLaVAAgent(
            name="TestAgent",
            llm_config={
                "timeout": 600,
                "seed": 42,
                "config_list": [{"model": "llava-fake", "base_url": "localhost:8000", "api_key": "Fake"}],
            },
        )

    def test_init(self):
        self.assertIsInstance(self.agent, LLaVAAgent)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestLLavaCallBinaryWithConfig(unittest.TestCase):
    @patch("requests.post")
    def test_local_mode(self, mock_post):
        # Mocking the response of requests.post
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"text":"response text"}']
        mock_post.return_value = mock_response

        # Calling the function
        output = _llava_call_binary_with_config(
            prompt="Test Prompt",
            images=[],
            config={"base_url": "http://0.0.0.0/api", "model": "test-model"},
            max_new_tokens=1000,
            temperature=0.5,
            seed=1,
        )

        # Verifying the results
        self.assertEqual(output, "response text")
        mock_post.assert_called_once_with(
            "http://0.0.0.0/api/worker_generate_stream",
            headers={"User-Agent": "LLaVA Client"},
            json={
                "model": "test-model",
                "prompt": "Test Prompt",
                "max_new_tokens": 1000,
                "temperature": 0.5,
                "stop": "###",
                "images": [],
            },
            stream=False,
        )

    @patch("replicate.run")
    def test_remote_mode(self, mock_run):
        # Mocking the response of replicate.run
        mock_run.return_value = iter(["response ", "text"])

        # Calling the function
        output = _llava_call_binary_with_config(
            prompt="Test Prompt",
            images=["image_data"],
            config={"base_url": "http://remote/api", "model": "test-model"},
            max_new_tokens=1000,
            temperature=0.5,
            seed=1,
        )

        # Verifying the results
        self.assertEqual(output, "response text")
        mock_run.assert_called_once_with(
            "http://remote/api",
            input={"image": "data:image/jpeg;base64,image_data", "prompt": "Test Prompt", "seed": 1},
        )


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestLLavaCall(unittest.TestCase):
    @patch("autogen.agentchat.contrib.llava_agent.llava_formater")
    @patch("autogen.agentchat.contrib.llava_agent.llava_call_binary")
    def test_llava_call(self, mock_llava_call_binary, mock_llava_formater):
        # Set up the mocks
        mock_llava_formater.return_value = ("formatted prompt", ["image1", "image2"])
        mock_llava_call_binary.return_value = "Generated Text"

        # Set up the llm_config dictionary
        llm_config = {
            "config_list": [{"api_key": "value", "base_url": "localhost:8000"}],
            "max_new_tokens": 2000,
            "temperature": 0.5,
            "seed": 1,
        }

        # Call the function
        result = llava_call("Test Prompt", llm_config)

        # Check the results
        mock_llava_formater.assert_called_once_with("Test Prompt", order_image_tokens=False)
        mock_llava_call_binary.assert_called_once_with(
            "formatted prompt",
            ["image1", "image2"],
            config_list=llm_config["config_list"],
            max_new_tokens=2000,
            temperature=0.5,
            seed=1,
        )
        self.assertEqual(result, "Generated Text")


if __name__ == "__main__":
    unittest.main()
