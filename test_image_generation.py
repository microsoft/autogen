import os
import re
from typing import Dict, Optional

import matplotlib.pyplot as plt
from PIL.Image import Image

import autogen
from autogen.agentchat.contrib import img_utils
from autogen.agentchat.contrib.capabilities import generate_images
from autogen.oai import openai_utils

CRITIC_SYSTEM_MESSAGE = """You need to improve the prompt of the figures you saw.
How to create a figure that is better in terms of color, shape, text (clarity), and other things.
Reply with the following format:

CRITICS: the image needs to improve...
PROMPT: here is the updated prompt!
"""

OAI_CONFIG_LIST = [
    {"model": "dall-e-3", "api_key": os.environ.get("OAI_API_KEY")},
    {"model": "gpt-4-vision-preview", "api_key": os.environ.get("OAI_API_KEY")},
    {"model": "gpt-3.5-turbo", "api_key": os.environ.get("OAI_API_KEY")},
]


def main():
    dalle = image_generator_agent()
    critic = critic_agent()

    img_prompt = "a happy robot is showing a sign with 'I Love AutoGen'"
    # img_prompt = "Ask me how I'm doing"

    dalle.initiate_chat(critic, message=img_prompt)

    img = extract_img(dalle, critic)
    img.show()


def image_generator_agent() -> autogen.ConversableAgent:
    agent = autogen.ConversableAgent(
        name="dalle", llm_config=gpt_config(), max_consecutive_auto_reply=2, human_input_mode="NEVER"
    )
    dalle_gen = generate_images.DalleImageGenerator(llm_config=dalle_config(), cache_settings={"directory": ".cache/"})
    image_gen_capability = generate_images.ImageGeneration(image_generator=dalle_gen)

    image_gen_capability.add_to_agent(agent)
    return agent


def critic_agent() -> autogen.ConversableAgent:
    return autogen.ConversableAgent(
        name="critic",
        llm_config=gpt_v_config(),
        system_message=CRITIC_SYSTEM_MESSAGE,
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
    )


def extract_img(sender: autogen.ConversableAgent, recipient: autogen.ConversableAgent) -> Image:
    """
    Extracts an image from the last message of an agent and converts it to a PIL image.

    This function searches the last message sent by the given agent for an image tag,
    extracts the image data, and then converts this data into a PIL (Python Imaging Library) image object.

    Parameters:
        agent (Agent): An instance of an agent from which the last message will be retrieved.

    Returns:
        PIL.Image: A PIL image object created from the extracted image data.

    Note:
    - The function assumes that the last message contains an <img> tag with image data.
    - The image data is extracted using a regular expression that searches for <img> tags.
    - It's important that the agent's last message contains properly formatted image data for successful extraction.
    - The `_to_pil` function is used to convert the extracted image data into a PIL image.
    - If no <img> tag is found, or if the image data is not correctly formatted, the function may raise an error.
    """
    img_data = None
    last_message = sender.last_message(recipient)["content"]

    if isinstance(last_message, str):
        img_data = re.findall("<img (.*)>", last_message)[0]
    elif isinstance(last_message, list):
        # The GPT-4V format, where the content is an array of data
        assert isinstance(last_message[0], dict)
        for msg in last_message:
            if msg["type"] == "image_url":
                img_data = msg["image_url"]["url"]
                break

    if img_data is None:
        raise ValueError("No image data found in the last message.")

    return img_utils.get_pil_image(img_data)


def gpt_config() -> Dict:
    filtered_configs = openai_utils.filter_config(OAI_CONFIG_LIST, filter_dict={"model": ["gpt-3.5-turbo"]})

    return {"config_list": filtered_configs, "timeout": 120, "temperature": 0.7}


def gpt_v_config() -> Dict:
    filtered_configs = openai_utils.filter_config(OAI_CONFIG_LIST, filter_dict={"model": ["gpt-4-vision-preview"]})

    return {"config_list": filtered_configs, "timeout": 120, "temperature": 0.7, "max_tokens": 1000}


def dalle_config() -> Dict:
    filtered_configs = openai_utils.filter_config(OAI_CONFIG_LIST, filter_dict={"model": ["dall-e-3"]})

    return {"config_list": filtered_configs, "timeout": 120, "temperature": 0.7}


if __name__ == "__main__":
    main()
