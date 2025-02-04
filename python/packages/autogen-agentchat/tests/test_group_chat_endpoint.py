import os

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient


@pytest.mark.asyncio
async def test_selector_group_chat_gemini() -> None:
    try:
        api_key = os.environ["GEMINI_API_KEY"]
    except KeyError:
        pytest.skip("GEMINI_API_KEY not set in environment variables.")

    model_client = OpenAIChatCompletionClient(
        model="gemini-1.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=api_key,
        model_info={
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.GEMINI_1_5_FLASH,
        },
    )

    assistant = AssistantAgent(
        "assistant",
        description="A helpful assistant agent.",
        model_client=model_client,
        system_message="You are a helpful assistant.",
    )

    critic = AssistantAgent(
        "critic",
        description="A critic agent to provide feedback.",
        model_client=model_client,
        system_message="Provide feedback.",
    )

    team = SelectorGroupChat([assistant, critic], model_client=model_client, max_turns=2)
    await Console(team.run_stream(task="Draft a short email about organizing a holiday party for new year."))
