#!/usr/bin/env python3 -m pytest

import asyncio
import os
import sys

import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

import autogen

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import reason, skip_openai

func_def = {
    "name": "get_random_number",
    "description": "Get a random number between 0 and 100",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
@pytest.mark.parametrize(
    "key, value, sync",
    [
        ("tools", [{"type": "function", "function": func_def}], False),
        ("functions", [func_def], True),
        ("tools", [{"type": "function", "function": func_def}], True),
    ],
)
@pytest.mark.asyncio
async def test_function_call_groupchat(key, value, sync):
    import random

    class Function:
        call_count = 0

        def get_random_number(self):
            self.call_count += 1
            return random.randint(0, 100)

    # llm_config without functions
    config_list_35 = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]},
    )
    llm_config_no_function = {"config_list": config_list_35}
    config_list_tool = autogen.filter_config(config_list_35, {"tags": ["tool"]})
    llm_config = {
        "config_list": config_list_tool,
        key: value,
    }

    func = Function()
    user_proxy = autogen.UserProxyAgent(
        name="Executor",
        description="An executor that executes function_calls.",
        function_map={"get_random_number": func.get_random_number},
        human_input_mode="NEVER",
    )
    player = autogen.AssistantAgent(
        name="Player",
        system_message="You will use function `get_random_number` to get a random number. Stop only when you get at least 1 even number and 1 odd number. Reply TERMINATE to stop.",
        description="A player that makes function_calls.",
        llm_config=llm_config,
    )
    observer = autogen.AssistantAgent(
        name="Observer",
        system_message="You observe the the player's actions and results. Summarize in 1 sentence.",
        description="An observer.",
        llm_config=llm_config_no_function,
    )
    groupchat = autogen.GroupChat(
        agents=[player, user_proxy, observer], messages=[], max_round=7, speaker_selection_method="round_robin"
    )

    # pass in llm_config with functions
    with pytest.raises(
        ValueError,
        match="GroupChatManager is not allowed to make function/tool calls. Please remove the 'functions' or 'tools' config in 'llm_config' you passed in.",
    ):
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_no_function)

    if sync:
        res = observer.initiate_chat(manager, message="Let's start the game!", summary_method="reflection_with_llm")
    else:
        res = await observer.a_initiate_chat(
            manager, message="Let's start the game!", summary_method="reflection_with_llm"
        )
    assert func.call_count >= 1, "The function get_random_number should be called at least once."
    print("Chat summary:", res.summary)
    print("Chat cost:", res.cost)


def test_no_function_map():
    dummy1 = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin that will execute function_calls.",
        human_input_mode="NEVER",
    )

    dummy2 = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin that will execute function_calls.",
        human_input_mode="NEVER",
    )
    groupchat = autogen.GroupChat(agents=[dummy1, dummy2], messages=[], max_round=7)
    groupchat.messages = [
        {
            "role": "assistant",
            "content": None,
            "function_call": {"name": "get_random_number", "arguments": "{}"},
        }
    ]
    with pytest.raises(
        ValueError,
        match="No agent can execute the function get_random_number. Please check the function_map of the agents.",
    ):
        groupchat._prepare_and_select_agents(dummy2)


if __name__ == "__main__":
    asyncio.run(test_function_call_groupchat("functions", [func_def], True))
    # test_no_function_map()
