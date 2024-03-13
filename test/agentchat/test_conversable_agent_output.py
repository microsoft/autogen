#!/usr/bin/env python3 -m pytest

import os
import sys
import time
import unittest
from typing import Any, Callable, Dict, Literal
from unittest.mock import MagicMock, patch

import pytest
from conftest import MOCK_OPEN_AI_API_KEY, skip_openai
from pydantic import BaseModel, Field
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from typing_extensions import Annotated

import autogen
from autogen.agentchat import ConversableAgent, UserProxyAgent
from autogen.agentchat.conversable_agent import register_function
from autogen.exception_utils import InvalidCarryOverType, SenderRequired

try:
    import openai
except ImportError:
    skip = True
else:
    skip = False or skip_openai

here = os.path.abspath(os.path.dirname(__file__))


class TestOutput:
    @pytest.mark.parametrize("stream", [True, False])
    def setup_method(self, stream: bool) -> None:
        config_list = autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            filter_dict={
                "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
            },
            file_location=KEY_LOC,
        )

        llm_config = {
            "config_list": config_list,
            "stream": stream,
        }

        self.agent = autogen.AssistantAgent(
            name="chatbot",
            system_message="For coding tasks, only use the functions you have been provided with. Reply TERMINATE when the task is done.",
            llm_config=llm_config,
        )

        # create a UserProxyAgent instance named "user_proxy"
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            system_message="A proxy for the user capable of calling functions and executing code.",
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config={"work_dir": "coding"},
        )

    @pytest.mark.skipif(
        skip or not sys.version.startswith("3.10"),
        reason="do not run if openai is not installed or py!=3.10",
    )
    @patch("autogen.io.IOConsole.output")
    def test_llm_messages(self, mock_print: MagicMock) -> None:
        self.user_proxy.initiate_chat(  # noqa: F704
            self.agent,
            message="Write a poem about Paris.",
        )

        # # define functions according to the function description
        # timer_mock = unittest.mock.MagicMock()
        # stopwatch_mock = unittest.mock.MagicMock()

        # # An example async function registered using decorators
        # @user_proxy.register_for_execution()
        # @agent.register_for_llm(description="create a timer for N seconds")
        # def timer(num_seconds: Annotated[str, "Number of seconds in the timer."]) -> str:
        #     print("timer is running")
        #     for i in range(int(num_seconds)):
        #         print(".", end="")
        #         time.sleep(0.01)
        #     print()

        #     timer_mock(num_seconds=num_seconds)
        #     return "Timer is done!"

        # # An example sync function registered using register_function
        # def stopwatch(num_seconds: Annotated[str, "Number of seconds in the stopwatch."]) -> str:
        #     print("stopwatch is running")
        #     # assert False, "stopwatch's alive!"
        #     for i in range(int(num_seconds)):
        #         print(".", end="")
        #         time.sleep(0.01)
        #     print()

        #     stopwatch_mock(num_seconds=num_seconds)
        #     return "Stopwatch is done!"

        # register_function(stopwatch, caller=agent, executor=user_proxy, description="create a stopwatch for N seconds")

        # # start the conversation
        # # 'await' is used to pause and resume code execution for async IO operations.
        # # Without 'await', an async function returns a coroutine object but doesn't execute the function.
        # # With 'await', the async function is executed and the current function is paused until the awaited function returns a result.
        # user_proxy.initiate_chat(  # noqa: F704
        #     agent,
        #     message="Create a timer for 2 seconds and then a stopwatch for 3 seconds.",
        # )

        # timer_mock.assert_called_once_with(num_seconds="2")
        # stopwatch_mock.assert_called_once_with(num_seconds="3")
