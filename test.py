import os

from autogen import ConversableAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.capabilities.generate_images import DalleImageGenerator, ImageGeneration
from autogen.agentchat.contrib.capabilities.modality_translator import ImageToText, ModalityTranslator
from autogen.agentchat.user_proxy_agent import UserProxyAgent

MAIN_SYSTEM_MESSAGE = """You are partaking in a two player:

- player 1: whispers the animal name to player 2
- player 2: needs to draw the animal
- player 3: needs to guess what is in the image
"""

BLIND_AGENT_SYSTEM_MESSAGE = """You are player 1: you must always respond in this format:
PROMPT: Draw me an animal. Replace the word animal with any animal of your choosing.

e.g. PROMPT: Draw me a zebra.
"""
PAINTER_AGENT_SYSTEM_MESSAGE = """You are player 2: you must draw the animal."""

CAPABLE_AGENT_SYSTEM_MESSAGE = """You are player 3: you must guess which animal is in the image."""

user_agent = UserProxyAgent(name="user_agent", human_input_mode="NEVER")

blind_agent = ConversableAgent(
    name="blind_agent",
    system_message=MAIN_SYSTEM_MESSAGE + BLIND_AGENT_SYSTEM_MESSAGE,
    llm_config={"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]},
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
)

painter_agent = ConversableAgent(
    name="painter_agent",
    system_message=MAIN_SYSTEM_MESSAGE + PAINTER_AGENT_SYSTEM_MESSAGE,
    llm_config={"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]},
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
)

capable_agent = ConversableAgent(
    name="capable_agent",
    system_message=MAIN_SYSTEM_MESSAGE + CAPABLE_AGENT_SYSTEM_MESSAGE,
    llm_config={"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"], "cache_seed": None},
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
)

gc = GroupChat(
    agents=[blind_agent, painter_agent, capable_agent], messages=[], speaker_selection_method="round_robin", max_round=4
)
manager = GroupChatManager(groupchat=gc)

image_to_text = ImageToText()
modality_translator = ModalityTranslator(modalities=["text"], translators=[image_to_text])
modality_translator.add_to_agent(capable_agent)

llm_config = {"config_list": [{"model": "dall-e-3", "api_key": os.environ["OPENAI_API_KEY"]}]}
dalle = DalleImageGenerator(llm_config=llm_config)
image_generator = ImageGeneration(image_generator=dalle)
image_generator.add_to_agent(painter_agent)

user_agent.send("Let's start the game", blind_agent, request_reply=True)
blind_agent.send(user_agent.last_message(blind_agent), painter_agent, request_reply=True)
painter_agent.send(blind_agent.last_message(painter_agent), capable_agent, request_reply=True)
capable_agent.send(painter_agent.last_message(capable_agent), user_agent, request_reply=True)
