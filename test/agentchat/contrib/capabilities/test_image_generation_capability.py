import itertools
import os
import tempfile
from typing import Any, Dict, Tuple

import pytest
from conftest import skip_openai  # noqa: E402
from PIL import Image

from autogen import code_utils
from autogen.agentchat.contrib.capabilities import generate_images
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.agentchat.user_proxy_agent import UserProxyAgent
from autogen.oai import openai_utils

# from test_assistant_agent import OAI_CONFIG_LIST, KEY_LOC  # noqa: E402


try:
    from openai import OpenAI
except ImportError:
    skip_test = True
else:
    skip_test = False or skip_openai

filter_dict = {"model": ["gpt-35-turbo-16k", "gpt-3.5-turbo-16k"]}

RESOLUTIONS = ["256x256", "512x512", "1024x1024"]
QUALITIES = ["standard", "hd"]
PROMPTS = [
    "Generate an image of a robot holding a 'I Love Autogen' sign",
    "Generate an image of a dog holding a 'I Love Autogen' sign",
]


@pytest.fixture
def dalle_config() -> Dict[str, Any]:
    config_list = [
        {
            "model": "dall-e-2",
            "api_key": os.environ.get("OPENAI_API_KEY"),
        }
    ]
    return {"config_list": config_list, "timeout": 120, "cache_seed": None}


# @pytest.fixture
# def gpt3_config() -> Dict[str, Any]:
#     config_list = openai_utils.config_list_from_json(
#         env_or_file=OAI_CONFIG_LIST, filter_dict=filter_dict, file_location=KEY_LOC
#     )
#     return {"config_list": config_list, "timeout": 120, "cache_seed": None}


@pytest.fixture
def gpt3_config():
    config = [
        {
            "model": "gpt-3.5-turbo-16k",
            "api_key": os.environ.get("OPENAI_API_KEY"),
        }
    ]
    return {"config_list": config, "timeout": 120, "cache_seed": None}


@pytest.fixture
def image_generator() -> generate_images.ImageGenerator:
    class TestImageGenerator:
        def generate_image(self, prompt: str):
            return Image.new("RGB", (256, 256))

        def cache_key(self, prompt: str):
            return prompt

    return TestImageGenerator()


@pytest.fixture
def image_gen_capability(image_generator: generate_images.ImageGenerator):
    return generate_images.ImageGeneration(image_generator)


def dalle_image_generator(dalle_config: Dict[str, Any], resolution: str, quality: str):
    return generate_images.DalleImageGenerator(dalle_config, resolution=resolution, quality=quality, num_images=1)


@pytest.mark.skipif(skip_test, reason="openai not installed OR requested to skip")
def test_dalle_image_generator(dalle_config: Dict[str, Any]):
    """Tests DalleImageGenerator capability to generate images by calling the OpenAI API."""
    dalle_generator = dalle_image_generator(dalle_config, RESOLUTIONS[0], QUALITIES[0])
    image = dalle_generator.generate_image(PROMPTS[0])

    assert isinstance(image, Image.Image)


# Using cartesian product to generate all possible combinations of resolution, quality, and prompt
@pytest.mark.parametrize("gen_config_1", itertools.product(RESOLUTIONS, QUALITIES, PROMPTS))
@pytest.mark.parametrize("gen_config_2", itertools.product(RESOLUTIONS, QUALITIES, PROMPTS))
def test_dalle_image_generator_cache_key(
    dalle_config: Dict[str, Any], gen_config_1: Tuple[str, str, str], gen_config_2: Tuple[str, str, str]
):
    """Tests if DalleImageGenerator creates unique cache keys.

    Args:
        dalle_config: The LLM config for the DalleImageGenerator.
        gen_config_1: A tuple containing the resolution, quality, and prompt for the first image generator.
        gen_config_2: A tuple containing the resolution, quality, and prompt for the second image generator.
    """
    dalle_generator_1 = dalle_image_generator(dalle_config, resolution=gen_config_1[0], quality=gen_config_1[1])
    dalle_generator_2 = dalle_image_generator(dalle_config, resolution=gen_config_2[0], quality=gen_config_2[1])

    cache_key_1 = dalle_generator_1.cache_key(gen_config_1[2])
    cache_key_2 = dalle_generator_2.cache_key(gen_config_2[2])

    if gen_config_1 == gen_config_2:
        assert cache_key_1 == cache_key_2
    else:
        assert cache_key_1 != cache_key_2


def test_image_generation_capability_positive(monkeypatch, image_gen_capability: generate_images.ImageGeneration):
    """Tests ImageGeneration capability to generate images by calling the ImageGenerator.

    This tests if the message is asking the agent to generate an image.
    """
    auto_reply = "Didn't need to generate an image."

    # Patching the _should_generate_image and _extract_prompt to avoid TextAnalyzerAgent to make API calls
    # Improves reproducibility and falkiness of the test
    monkeypatch.setattr(generate_images.ImageGeneration, "_should_generate_image", lambda _, __: True)
    monkeypatch.setattr(generate_images.ImageGeneration, "_extract_prompt", lambda _, __: PROMPTS[0])

    user = UserProxyAgent("user", human_input_mode="NEVER")
    agent = ConversableAgent("test_agent", llm_config=False, default_auto_reply=auto_reply)
    image_gen_capability.add_to_agent(agent)

    user.send(message=PROMPTS[0], recipient=agent, request_reply=True, silent=True)
    last_message = agent.last_message()

    assert last_message

    processed_message = code_utils.content_str(last_message["content"])

    assert "<image>" in processed_message
    assert auto_reply not in processed_message


def test_image_generation_capability_negative(monkeypatch, image_gen_capability: generate_images.ImageGeneration):
    """Tests ImageGeneration capability to generate images by calling the ImageGenerator.

    This tests if the message is not asking the agent to generate an image.
    """
    auto_reply = "Didn't need to generate an image."

    # Patching the _should_generate_image and _extract_prompt to avoid TextAnalyzerAgent to make API calls
    # Improves reproducibility and falkiness of the test
    monkeypatch.setattr(generate_images.ImageGeneration, "_should_generate_image", lambda _, __: False)
    monkeypatch.setattr(generate_images.ImageGeneration, "_extract_prompt", lambda _, __: PROMPTS[0])

    user = UserProxyAgent("user", human_input_mode="NEVER")
    agent = ConversableAgent("test_agent", llm_config=False, default_auto_reply=auto_reply)
    image_gen_capability.add_to_agent(agent)

    user.send(message=PROMPTS[0], recipient=agent, request_reply=True, silent=True)
    last_message = agent.last_message()

    assert last_message

    processed_message = code_utils.content_str(last_message["content"])

    assert "<image>" not in processed_message
    assert auto_reply == processed_message
