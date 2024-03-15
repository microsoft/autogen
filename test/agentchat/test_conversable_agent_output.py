#!/usr/bin/env python3 -m pytest

import os
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from typing import Any, Callable, Dict, Literal
from unittest.mock import MagicMock, patch

import pytest
from autogen.cache.cache import Cache
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


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
@pytest.mark.parametrize("stream", [True, False])
class TestOutput:
    @pytest.fixture(scope="function", autouse=True)
    def setup_and_teardown(self, stream: bool) -> None:
        assert stream in [True, False]

        config_list = autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            filter_dict={
                "model": ["gpt-3.5-turbo", "gpt-4", "gpt-4-32k"],
            },
            file_location=KEY_LOC,
        )

        llm_config = {
            "config_list": config_list,
            "stream": stream,
        }

        self.agent = autogen.AssistantAgent(
            name="chatbot",
            system_message="You are a helpful assistant that is given a single task. Use only the functions you have been provided with. "
            "Do not forget to write 'TERMINATE' when the task is done in the last line of the response. "
            "Do not ask for further instructions after the task is done.",
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

        @self.user_proxy.register_for_execution()
        @self.agent.register_for_llm(description="Get the weather forecast for a location.")
        def get_weather(location: Annotated[str, "The location to get the weather forecast for."]) -> str:
            return f"The weather in {location} is sunny."

        with TemporaryDirectory() as t:
            with Cache.disk(cache_path_root=t) as cache:
                self.cache = cache if stream else None
                yield

    @patch("autogen.io.IOConsole.output")
    def test_llm_messages(self, mock_output: MagicMock, stream: bool) -> None:
        self.user_proxy.initiate_chat(  # noqa: F704
            self.agent,
            message="Write a haiku about Paris.",
            cache=self.cache,
        )

    @patch("autogen.io.IOConsole.output")
    def test_tool_function_call_messages(self, mock_output: MagicMock, stream: bool) -> None:
        self.user_proxy.initiate_chat(  # noqa: F704
            self.agent,
            message="Check the weather forecast in Paris and then write a haiku about it.",
            cache=self.cache,
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
