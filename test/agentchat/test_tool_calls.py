#!/usr/bin/env python3 -m pytest

import inspect
import json
import os
import sys

import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

import autogen
from autogen.math_utils import eval_math_responses
from autogen.oai.client import TOOL_ENABLED

try:
    from openai import OpenAI
except ImportError:
    skip_openai = True
else:
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from conftest import skip_openai


@pytest.mark.skipif(skip_openai or not TOOL_ENABLED, reason="openai>=1.1.0 not installed or requested to skip")
def test_eval_math_responses():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        KEY_LOC,
        filter_dict={"tags": ["tool"]},
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "eval_math_responses",
                "description": "Select a response for a math problem using voting, and check if the response is correct if the solution is provided",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "responses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The responses in a list",
                        },
                        "solution": {
                            "type": "string",
                            "description": "The canonical solution",
                        },
                    },
                    "required": ["responses"],
                },
            },
        },
    ]
    client = autogen.OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[
            {
                "role": "user",
                "content": 'evaluate the math responses ["1", "5/2", "5/2"] against the true answer \\frac{5}{2}',
            },
        ],
        tools=tools,
    )
    print(response)
    responses = client.extract_text_or_completion_object(response)
    print(responses[0])
    tool_calls = responses[0].tool_calls
    function_call = tool_calls[0].function
    name, arguments = function_call.name, json.loads(function_call.arguments)
    assert name == "eval_math_responses"
    print(arguments["responses"])
    # if isinstance(arguments["responses"], str):
    #     arguments["responses"] = json.loads(arguments["responses"])
    arguments["responses"] = [f"\\boxed{{{x}}}" for x in arguments["responses"]]
    print(arguments["responses"])
    arguments["solution"] = f"\\boxed{{{arguments['solution']}}}"
    print(eval_math_responses(**arguments))


@pytest.mark.skipif(skip_openai or not TOOL_ENABLED, reason="openai>=1.1.0 not installed or requested to skip")
def test_eval_math_responses_api_style_function():
    # config_list = autogen.config_list_from_models(
    #     KEY_LOC,
    #     model_list=["gpt-4-0613", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k"],
    # )

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        KEY_LOC,
        filter_dict={"tags": ["tool"]},
    )
    functions = [
        {
            "name": "eval_math_responses",
            "description": "Select a response for a math problem using voting, and check if the response is correct if the solution is provided",
            "parameters": {
                "type": "object",
                "properties": {
                    "responses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The responses in a list",
                    },
                    "solution": {
                        "type": "string",
                        "description": "The canonical solution",
                    },
                },
                "required": ["responses"],
            },
        },
    ]
    client = autogen.OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[
            {
                "role": "user",
                "content": 'evaluate the math responses ["1", "5/2", "5/2"] against the true answer \\frac{5}{2}',
            },
        ],
        functions=functions,
    )
    print(response)
    responses = client.extract_text_or_completion_object(response)
    print(responses[0])
    function_call = responses[0].function_call
    name, arguments = function_call.name, json.loads(function_call.arguments)
    assert name == "eval_math_responses"
    print(arguments["responses"])
    # if isinstance(arguments["responses"], str):
    #     arguments["responses"] = json.loads(arguments["responses"])
    arguments["responses"] = [f"\\boxed{{{x}}}" for x in arguments["responses"]]
    print(arguments["responses"])
    arguments["solution"] = f"\\boxed{{{arguments['solution']}}}"
    print(eval_math_responses(**arguments))


@pytest.mark.skipif(
    skip_openai or not TOOL_ENABLED or not sys.version.startswith("3.10"),
    reason="do not run if openai is <1.1.0 or py!=3.10 or requested to skip",
)
def test_update_tool():
    config_list_gpt4 = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "tags": ["gpt-4"],
        },
        file_location=KEY_LOC,
    )
    llm_config = {
        "config_list": config_list_gpt4,
        "seed": 42,
        "tools": [],
    }

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
    )
    assistant = autogen.AssistantAgent(name="test", llm_config=llm_config)

    # Define a new function *after* the assistant has been created
    assistant.update_tool_signature(
        {
            "type": "function",
            "function": {
                "name": "greet_user",
                "description": "Greets the user.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        is_remove=False,
    )
    res = user_proxy.initiate_chat(
        assistant,
        message="What functions do you know about in the context of this conversation? End your response with 'TERMINATE'.",
    )
    messages1 = assistant.chat_messages[user_proxy][-1]["content"]
    print("Message:", messages1)
    print("Summary:", res.summary)
    assert (
        messages1.replace("TERMINATE", "") == res.summary
    ), "Message (removing TERMINATE) and summary should be the same"

    assistant.update_tool_signature("greet_user", is_remove=True)
    res = user_proxy.initiate_chat(
        assistant,
        message="What functions do you know about in the context of this conversation? End your response with 'TERMINATE'.",
        summary_method="reflection_with_llm",
    )
    messages2 = assistant.chat_messages[user_proxy][-1]["content"]
    print("Message2:", messages2)
    # The model should know about the function in the context of the conversation
    assert "greet_user" in messages1
    assert "greet_user" not in messages2
    print("Summary2:", res.summary)


@pytest.mark.skipif(not TOOL_ENABLED, reason="openai>=1.1.0 not installed")
def test_multi_tool_call():
    class FakeAgent(autogen.Agent):
        def __init__(self, name):
            self._name = name
            self.received = []
            self.silent = False

        @property
        def name(self):
            return self._name

        @property
        def description(self):
            return self._name

        def receive(
            self,
            message,
            sender,
            request_reply=None,
            silent=False,
        ):
            message = message if isinstance(message, list) else [message]
            self.received.extend(message)

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
    )
    user_proxy.register_function({"echo": lambda str: str})

    fake_agent = FakeAgent("fake_agent")

    user_proxy.receive(
        message={
            "content": "test multi tool call",
            "tool_calls": [
                {
                    "id": "tool_1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": json.JSONEncoder().encode({"str": "hello world"})},
                },
                {
                    "id": "tool_2",
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "arguments": json.JSONEncoder().encode({"str": "goodbye and thanks for all the fish"}),
                    },
                },
                {
                    "id": "tool_3",
                    "type": "function",
                    "function": {
                        "name": "multi_tool_call_echo",  # normalized "multi_tool_call.echo"
                        "arguments": json.JSONEncoder().encode({"str": "goodbye and thanks for all the fish"}),
                    },
                },
            ],
        },
        sender=fake_agent,
        request_reply=True,
    )

    assert fake_agent.received == [
        {
            "role": "tool",
            "tool_responses": [
                {"tool_call_id": "tool_1", "role": "tool", "content": "hello world"},
                {
                    "tool_call_id": "tool_2",
                    "role": "tool",
                    "content": "goodbye and thanks for all the fish",
                },
                {
                    "tool_call_id": "tool_3",
                    "role": "tool",
                    "content": "Error: Function multi_tool_call_echo not found.",
                },
            ],
            "content": inspect.cleandoc(
                """
                hello world

                goodbye and thanks for all the fish

                Error: Function multi_tool_call_echo not found.
                """
            ),
        }
    ]


@pytest.mark.skipif(not TOOL_ENABLED, reason="openai>=1.1.0 not installed")
@pytest.mark.asyncio
async def test_async_multi_tool_call():
    class FakeAgent(autogen.Agent):
        def __init__(self, name):
            self._name = name
            self.received = []
            self.silent = False

        @property
        def name(self):
            return self._name

        @property
        def description(self):
            return self._name

        async def a_receive(
            self,
            message,
            sender,
            request_reply=None,
            silent=False,
        ):
            message = message if isinstance(message, list) else [message]
            self.received.extend(message)
            return ""

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
    )

    def echo(str):
        return str

    async def a_echo(str):
        return str

    user_proxy.register_function({"a_echo": a_echo, "echo": echo})

    fake_agent = FakeAgent("fake_agent")

    await user_proxy.a_receive(
        message={
            "content": "test multi tool call",
            "tool_calls": [
                {
                    "id": "tool_1",
                    "type": "function",
                    "function": {"name": "a_echo", "arguments": json.JSONEncoder().encode({"str": "hello world"})},
                },
                {
                    "id": "tool_2",
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "arguments": json.JSONEncoder().encode({"str": "goodbye and thanks for all the fish"}),
                    },
                },
                {
                    "id": "tool_3",
                    "type": "function",
                    "function": {
                        "name": "multi_tool_call_echo",  # normalized "multi_tool_call.echo"
                        "arguments": json.JSONEncoder().encode({"str": "goodbye and thanks for all the fish"}),
                    },
                },
            ],
        },
        sender=fake_agent,
        request_reply=True,
    )

    assert fake_agent.received == [
        {
            "role": "tool",
            "tool_responses": [
                {"tool_call_id": "tool_1", "role": "tool", "content": "hello world"},
                {
                    "tool_call_id": "tool_2",
                    "role": "tool",
                    "content": "goodbye and thanks for all the fish",
                },
                {
                    "tool_call_id": "tool_3",
                    "role": "tool",
                    "content": "Error: Function multi_tool_call_echo not found.",
                },
            ],
            "content": inspect.cleandoc(
                """
                hello world

                goodbye and thanks for all the fish

                Error: Function multi_tool_call_echo not found.
                """
            ),
        }
    ]


if __name__ == "__main__":
    test_update_tool()
    # test_eval_math_responses()
    # test_multi_tool_call()
    # test_eval_math_responses_api_style_function()
