#!/usr/bin/env python3 -m pytest

import asyncio
import os
import sys
from unittest.mock import AsyncMock

import autogen
import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
@pytest.mark.asyncio
async def test_async_get_human_input():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        max_consecutive_auto_reply=2,
        llm_config={"seed": 41, "config_list": config_list, "temperature": 0},
    )

    user_proxy = autogen.UserProxyAgent(name="user", human_input_mode="ALWAYS", code_execution_config=False)

    user_proxy.a_get_human_input = AsyncMock(return_value="This is a test")

    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.a_check_termination_and_human_reply)

    await user_proxy.a_initiate_chat(assistant, clear_history=True, message="Hello.")
    # Test without message
    res = await user_proxy.a_initiate_chat(assistant, clear_history=True, summary_method="reflection_with_llm")
    # Assert that custom a_get_human_input was called at least once
    user_proxy.a_get_human_input.assert_called()
    print("Result summary:", res.summary)
    print("Human input:", res.human_input)


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
@pytest.mark.asyncio
async def test_async_max_turn():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        max_consecutive_auto_reply=10,
        llm_config={
            "seed": 41,
            "config_list": config_list,
        },
    )

    user_proxy = autogen.UserProxyAgent(name="user", human_input_mode="ALWAYS", code_execution_config=False)

    user_proxy.a_get_human_input = AsyncMock(return_value="Not funny. Try again.")

    res = await user_proxy.a_initiate_chat(
        assistant, clear_history=True, max_turns=3, message="Hello, make a joke about AI."
    )
    print("Result summary:", res.summary)
    print("Human input:", res.human_input)
    print("chat history:", res.chat_history)
    assert (
        len(res.chat_history) == 6
    ), f"Chat history should have 6 messages because max_turns is set to 3 (and user keep request try again) but has {len(res.chat_history)}."


if __name__ == "__main__":
    asyncio.run(test_async_get_human_input())
    asyncio.run(test_async_max_turn())
