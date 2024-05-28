#!/usr/bin/env python3 -m pytest

import os
import sys
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock

import pytest

from autogen import OpenAIWrapper, config_list_from_json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai

    # raises exception if openai>=1 is installed and something is wrong with imports
    # otherwise the test will be skipped
    from openai.types.chat.chat_completion import ChatCompletionMessage  # type: ignore [attr-defined]
    from openai.types.chat.chat_completion_chunk import (
        ChoiceDeltaFunctionCall,
        ChoiceDeltaToolCall,
        ChoiceDeltaToolCallFunction,
    )

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_aoai_chat_completion_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_completion_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "1+1="}], stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


# no need for OpenAI, works with any model
def test__update_dict_from_chunk() -> None:
    # dictionaries and lists are not supported
    mock = MagicMock()
    empty_collections: List[Union[List[Any], Dict[str, Any]]] = [{}, []]
    for c in empty_collections:
        mock.c = c
        with pytest.raises(NotImplementedError):
            OpenAIWrapper._update_dict_from_chunk(mock, {}, "c")

    org_d: Dict[str, Any] = {}
    for i, v in enumerate([0, 1, False, True, 0.0, 1.0]):
        field = "abcedfghijklmnopqrstuvwxyz"[i]
        setattr(mock, field, v)

        d = org_d.copy()
        OpenAIWrapper._update_dict_from_chunk(mock, d, field)

        org_d[field] = v
        assert d == org_d

    mock.s = "beginning"
    OpenAIWrapper._update_dict_from_chunk(mock, d, "s")
    assert d["s"] == "beginning"

    mock.s = " and"
    OpenAIWrapper._update_dict_from_chunk(mock, d, "s")
    assert d["s"] == "beginning and"

    mock.s = " end"
    OpenAIWrapper._update_dict_from_chunk(mock, d, "s")
    assert d["s"] == "beginning and end"


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test__update_function_call_from_chunk() -> None:
    function_call_chunks = [
        ChoiceDeltaFunctionCall(arguments=None, name="get_current_weather"),
        ChoiceDeltaFunctionCall(arguments='{"', name=None),
        ChoiceDeltaFunctionCall(arguments="location", name=None),
        ChoiceDeltaFunctionCall(arguments='":"', name=None),
        ChoiceDeltaFunctionCall(arguments="San", name=None),
        ChoiceDeltaFunctionCall(arguments=" Francisco", name=None),
        ChoiceDeltaFunctionCall(arguments='"}', name=None),
    ]
    expected = {"name": "get_current_weather", "arguments": '{"location":"San Francisco"}'}

    full_function_call = None
    completion_tokens = 0
    for function_call_chunk in function_call_chunks:
        # print(f"{function_call_chunk=}")
        full_function_call, completion_tokens = OpenAIWrapper._update_function_call_from_chunk(
            function_call_chunk=function_call_chunk,
            full_function_call=full_function_call,
            completion_tokens=completion_tokens,
        )

    print(f"{full_function_call=}")
    print(f"{completion_tokens=}")

    assert full_function_call == expected
    assert completion_tokens == len(function_call_chunks)

    ChatCompletionMessage(role="assistant", function_call=full_function_call, content=None)


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test__update_tool_calls_from_chunk() -> None:
    tool_calls_chunks = [
        ChoiceDeltaToolCall(
            index=0,
            id="call_D2HOWGMekmkxXu9Ix3DUqJRv",
            function=ChoiceDeltaToolCallFunction(arguments="", name="get_current_weather"),
            type="function",
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='{"lo', name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments="catio", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='n": "S', name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments="an F", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments="ranci", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments="sco, C", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=0, id=None, function=ChoiceDeltaToolCallFunction(arguments='A"}', name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1,
            id="call_22HgJep4nwoKU3UOr96xaLmd",
            function=ChoiceDeltaToolCallFunction(arguments="", name="get_current_weather"),
            type="function",
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments='{"lo', name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments="catio", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments='n": "N', name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments="ew Y", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments="ork, ", name=None), type=None
        ),
        ChoiceDeltaToolCall(
            index=1, id=None, function=ChoiceDeltaToolCallFunction(arguments='NY"}', name=None), type=None
        ),
    ]

    full_tool_calls: List[Optional[Dict[str, Any]]] = [None, None]
    completion_tokens = 0
    for tool_calls_chunk in tool_calls_chunks:
        index = tool_calls_chunk.index
        full_tool_calls[index], completion_tokens = OpenAIWrapper._update_tool_calls_from_chunk(
            tool_calls_chunk=tool_calls_chunk,
            full_tool_call=full_tool_calls[index],
            completion_tokens=completion_tokens,
        )

    print(f"{full_tool_calls=}")
    print(f"{completion_tokens=}")

    ChatCompletionMessage(role="assistant", tool_calls=full_tool_calls, content=None)


# todo: remove when OpenAI removes functions from the API
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_functions_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    functions = [
        {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                },
                "required": ["location"],
            },
        },
    ]
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[{"role": "user", "content": "What's the weather like today in San Francisco?"}],
        functions=functions,
        stream=True,
    )
    print(response)
    print(client.extract_text_or_completion_object(response))


# test for tool support instead of the deprecated function calls
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_tools_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["multitool"]},
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
    ]
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[{"role": "user", "content": "What's the weather like today in San Francisco?"}],
        tools=tools,
        stream=True,
    )
    # check response
    choices = response.choices
    assert isinstance(choices, list)
    assert len(choices) > 0

    choice = choices[0]
    assert choice.finish_reason == "tool_calls"

    message = choice.message
    tool_calls = message.tool_calls
    assert isinstance(tool_calls, list)
    assert len(tool_calls) > 0


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_completion_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"tags": ["gpt-3.5-turbo-instruct"]}
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=", stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


if __name__ == "__main__":
    # test_aoai_chat_completion_stream()
    # test_chat_completion_stream()
    # test_chat_functions_stream()
    # test_completion_stream()
    test_chat_tools_stream()
