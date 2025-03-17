import os
from typing import List, Sequence

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
)
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def _test_selector_group_chat(model_client: ChatCompletionClient) -> None:
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


async def _test_selector_group_chat_with_candidate_func(model_client: ChatCompletionClient) -> None:
    filtered_participants = ["developer", "tester"]

    def dummy_candidate_func(thread: Sequence[AgentEvent | ChatMessage]) -> List[str]:
        # Dummy candidate function that will return
        # only return developer and reviewer
        return filtered_participants

    developer = AssistantAgent(
        "developer",
        description="Writes and implements code based on requirements.",
        model_client=model_client,
        system_message="You are a software developer working on a new feature.",
    )

    tester = AssistantAgent(
        "tester",
        description="Writes and executes test cases to validate the implementation.",
        model_client=model_client,
        system_message="You are a software tester ensuring the feature works correctly.",
    )

    project_manager = AssistantAgent(
        "project_manager",
        description="Oversees the project and ensures alignment with the broader goals.",
        model_client=model_client,
        system_message="You are a project manager ensuring the team meets the project goals.",
    )

    team = SelectorGroupChat(
        participants=[developer, tester, project_manager],
        model_client=model_client,
        max_turns=3,
        candidate_func=dummy_candidate_func,
    )

    task = "Create a detailed implementation plan for adding dark mode in a React app and review it for feasibility and improvements."

    async for message in team.run_stream(task=task):
        if not isinstance(message, TaskResult):
            if message.source == "user":  # ignore the first 'user' message
                continue
            assert message.source in filtered_participants, "Candidate function didn't filter the participants"


@pytest.mark.asyncio
async def test_selector_group_chat_gemini() -> None:
    try:
        api_key = os.environ["GEMINI_API_KEY"]
    except KeyError:
        pytest.skip("GEMINI_API_KEY not set in environment variables.")

    model_client = OpenAIChatCompletionClient(
        model="gemini-1.5-flash",
        api_key=api_key,
    )
    await _test_selector_group_chat(model_client)
    await _test_selector_group_chat_with_candidate_func(model_client)


@pytest.mark.asyncio
async def test_selector_group_chat_openai() -> None:
    try:
        api_key = os.environ["OPENAI_API_KEY"]
    except KeyError:
        pytest.skip("OPENAI_API_KEY not set in environment variables.")

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key,
    )
    await _test_selector_group_chat(model_client)
    await _test_selector_group_chat_with_candidate_func(model_client)
