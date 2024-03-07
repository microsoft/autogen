import os
import re
from typing import Dict, Optional

import matplotlib.pyplot as plt
from PIL.Image import Image

import autogen
from autogen.agentchat import groupchat
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

    dalle.initiate_chat(critic, message=img_prompt, clear_history=False)


def image_generator_agent() -> autogen.ConversableAgent:
    agent = autogen.ConversableAgent(name="dalle", llm_config=gpt_config(), max_consecutive_auto_reply=2)
    dalle_gen = generate_images.DalleImageGenerator(llm_config=dalle_config(), cache_settings={"directory": ".cache/"})
    image_gen_capability = generate_images.ImageGeneration(image_generator=dalle_gen)

    image_gen_capability.add_to_agent(agent)
    return agent


def critic_agent() -> autogen.ConversableAgent:
    return autogen.ConversableAgent(
        name="critic", llm_config=gpt_v_config(), system_message=CRITIC_SYSTEM_MESSAGE, max_consecutive_auto_reply=2
    )


def art_studio() -> groupchat.GroupChatManager:
    gc = groupchat.GroupChat(
        admin_name=None,
        agents=[image_generator_agent(), critic_agent()],
        messages=[],
        speaker_selection_method="round_robin",
        max_round=4,
    )
    return groupchat.GroupChatManager(groupchat=gc, llm_config=False)


def extract_img(sender: autogen.ConversableAgent, recipient: autogen.ConversableAgent) -> Optional[Image]:
    # From notebook/agentchat_dalle_and_gpt4v.ipynb
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
    last_message = recipient.last_message(sender)
    print(f"Last message: {last_message}")
    img_data = None

    if isinstance(last_message, str):
        img_data = re.findall("<img (.*)>", last_message)
        if img_data:
            img_data = img_data[0]
    elif isinstance(last_message, list):
        # The GPT-4V format, where the content is an array of data
        assert isinstance(last_message[0], dict)
        img_data = last_message[0].get("image_url", {}).get("url")

    if img_data:
        return img_utils._to_pil(img_data)
    else:
        return None


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
