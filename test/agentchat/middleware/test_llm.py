import inspect
from typing import Any, Dict, List, Literal, Optional, Union
import unittest
from unittest.mock import AsyncMock, MagicMock
from openai import completions

import pytest
from autogen.oai.client import OpenAIWrapper
from conftest import skip_openai

import autogen
from autogen.agentchat.middleware.llm import LLMMiddleware

try:
    import openai
except ImportError:  # pragma: no cover
    skip = True
    Completions = object
    CompletionChoice = object
else:  # pragma: no cover
    skip = False or skip_openai
    from openai.types.completion import Completion, CompletionChoice  # type: ignore [assignment, attr-defined]


KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"

_tools = [
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
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_n_day_weather_forecast",
            "description": "Get an N-day weather forecast",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                    "num_days": {
                        "type": "integer",
                        "description": "The number of days to forecast",
                    },
                },
                "required": ["location", "format", "num_days"],
            },
        },
    },
]

funny_system_message = "You are a funny AI Assistant."


@pytest.mark.parametrize(
    "system_message",
    [
        None,
        funny_system_message,
        [{"content": funny_system_message, "role": "system"}],
        {"content": "should fail on dict", "role": "system"},
    ],
)
def test_init_system_message(system_message: Optional[Union[str, List[Dict[str, str]]]]) -> None:
    if isinstance(system_message, dict):
        with pytest.raises(ValueError) as e:
            md = LLMMiddleware(name="assistant", llm_config=False, system_message=system_message)
        assert "system_message must be a string or a list of messages, but got" in str(e.value)
    elif system_message is None:
        md = LLMMiddleware(name="assistant", llm_config=False)

        assert md.system_messages == [{"content": "You are a helpful AI Assistant.", "role": "system"}]

        with pytest.raises(ValueError) as e:
            md = LLMMiddleware(name="assistant", llm_config=False, system_message=None)  # type: ignore[arg-type]
        assert "system_message must be a string or a list of messages, but got" in str(e.value)
    else:
        for llm_config in [False, {}]:
            md = LLMMiddleware(name="assistant", llm_config=llm_config, system_message=system_message)  # type: ignore[arg-type]

        assert md.system_messages == [{"content": funny_system_message, "role": "system"}]

        with pytest.raises(ValueError) as e:
            md = LLMMiddleware(name="assistant", llm_config=None, system_message=system_message)
        assert "llm_config must be provided" in str(e.value)

        with pytest.raises(ValueError) as e:
            md = LLMMiddleware(name="assistant", llm_config=True, system_message=system_message)  # type: ignore[arg-type]
        assert "llm_config must be a dict or False, but got" in str(e.value)

        with pytest.raises(ValueError) as e:
            md = LLMMiddleware(name="assistant", llm_config="whatever", system_message=system_message)  # type: ignore[arg-type]
        assert "llm_config must be a dict or False, but got" in str(e.value)


if skip:  # pragma: no cover
    _config_list = []
else:  # pragma: no cover
    _config_list = autogen.config_list_from_json(  # pragma: no cover
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
@pytest.mark.parametrize(
    "llm_config, messages, retval, next_called",
    [
        # should call next
        (False, [{"role": "user", "content": "1+1="}], "Hello world!", True),
        # should get response from openai and not call next
        ({"cache_seed": None, "config_list": _config_list}, [{"role": "user", "content": "1+1="}], "2", False),
    ],
)
def test_llm(llm_config: Dict[str, Any], messages: List[Dict[str, str]], retval: str, next_called: bool) -> None:
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")

    next = MagicMock(return_value="Hello world!")

    reply: Dict[str, Any] = mw.call(messages=messages, next=next)  # type: ignore[assignment]

    assert retval in reply

    if next_called:
        next.assert_called_once()
    else:
        next.assert_not_called()


@pytest.mark.asyncio()
@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
@pytest.mark.parametrize(
    "llm_config, messages, retval, next_awaited",
    [
        # should call next
        (False, [{"role": "user", "content": "1+1="}], "Hello world!", True),
        # should get response from openai and not call next
        ({"cache_seed": None, "config_list": _config_list}, [{"role": "user", "content": "1+1="}], "2", False),
    ],
)
async def test_llm_async(
    llm_config: Dict[str, Any], messages: List[Dict[str, str]], retval: str, next_awaited: bool
) -> None:
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")

    next = AsyncMock(return_value="Hello world!")

    reply: Dict[str, Any] = await mw.a_call(messages=messages, next=next)  # type: ignore[assignment]

    assert retval in reply

    if next_awaited:
        next.assert_awaited_once()
    else:
        next.assert_not_awaited()


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
def test_llm_tool_calls() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    for tool in _tools:
        mw.update_tool_signature(tool, is_remove=None)

    messages = [{"role": "user", "content": "What's the current weather in New York?"}]
    reply: Dict[str, Any] = mw.call(messages=messages)  # type: ignore[assignment]
    assert reply["tool_calls"][0]["function"]["name"] == "get_current_weather"

    messages = [{"role": "user", "content": "What's the weather in New York for the next 5 days?"}]
    reply = mw.call(messages=messages)  # type: ignore[assignment]
    function_names = [tool["function"]["name"] for tool in reply["tool_calls"]]
    assert "get_n_day_weather_forecast" in function_names


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
def test_llm_tool_calls_parallel() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo-1106", "gpt-35-turbo-1106"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    for tool in _tools:
        mw.update_tool_signature(tool, is_remove=None)

    messages = [{"role": "user", "content": "What's the current weather in New York and San Francisco?"}]
    reply = mw.call(messages=messages)
    print(reply)
    assert len(reply["tool_calls"]) == 2  # type: ignore[index]
    assert reply["tool_calls"][0]["function"]["name"] == "get_current_weather"  # type: ignore[index]
    assert reply["tool_calls"][1]["function"]["name"] == "get_current_weather"  # type: ignore[index]


_exec_python_function_sig = {
    "description": "run cell in ipython and return the execution result.",
    "name": "python",
    "parameters": {
        "properties": {"cell": {"description": "Valid Python cell to execute.", "type": "string"}},
        "required": ["cell"],
        "type": "object",
    },
}

_exec_python_tool_sig = {
    "type": "function",
    "function": _exec_python_function_sig,
}

_exec_sh_function_sig = {
    "name": "sh",
    "description": "run a shell script and return the execution result.",
    "parameters": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "Valid shell script to execute.",
            }
        },
        "required": ["script"],
    },
}

_exec_sh_tool_sig = {
    "type": "function",
    "function": _exec_sh_function_sig,
}


def test_update_function_signature() -> None:
    md = LLMMiddleware(name="agent1", llm_config=False)
    with pytest.raises(ValueError) as e:
        md.update_function_signature({}, is_remove=False)

    assert "To update a function signature, agent must have an llm_config" in str(e.value)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        md = LLMMiddleware(name="agent1", llm_config={})

        md.update_function_signature(_exec_python_function_sig, is_remove=False)
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig]  # type: ignore[union-attr]

        md.update_function_signature(_exec_sh_function_sig, is_remove=False)
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig, _exec_sh_function_sig]  # type: ignore[union-attr]

        md.update_function_signature(_exec_sh_function_sig, is_remove=False)
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig, _exec_sh_function_sig]  # type: ignore[union-attr]

        md.update_function_signature(_exec_sh_function_sig["name"], is_remove=True)  # type: ignore[arg-type]
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig]  # type: ignore[union-attr]

        md.update_function_signature(_exec_python_function_sig["name"], is_remove=True)  # type: ignore[arg-type]
        assert "functions" not in md.client._config_list[0]  # type: ignore[union-attr]

        with pytest.raises(ValueError) as e:
            md.update_function_signature(_exec_python_function_sig["name"], is_remove=True)  # type: ignore[arg-type]
        assert "The agent config doesn't have function" in str(e.value)

        md.update_function_signature(_exec_python_function_sig, is_remove=False)
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig]  # type: ignore[union-attr]

        # I guess this is fine, but it's not what I expected
        md.update_function_signature("some_random_name", is_remove=True)
        assert md.client._config_list[0]["functions"] == [_exec_python_function_sig]  # type: ignore[union-attr]


def test_update_tools_signature() -> None:
    md = LLMMiddleware(name="agent1", llm_config=False)
    with pytest.raises(ValueError) as e:
        md.update_tool_signature({}, is_remove=False)

    assert "To update a tool signature, agent must have an llm_config" in str(e.value)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        md = LLMMiddleware(name="agent1", llm_config={})

        md.update_tool_signature(_exec_python_tool_sig, is_remove=False)
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig]  # type: ignore[union-attr]

        md.update_tool_signature(_exec_sh_tool_sig, is_remove=False)
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig, _exec_sh_tool_sig]  # type: ignore[union-attr]

        md.update_tool_signature(_exec_sh_tool_sig, is_remove=False)
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig, _exec_sh_tool_sig]  # type: ignore[union-attr]

        md.update_tool_signature(_exec_sh_tool_sig["function"]["name"], is_remove=True)  # type: ignore[index]
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig]  # type: ignore[union-attr]

        md.update_tool_signature(_exec_python_tool_sig["function"]["name"], is_remove=True)  # type: ignore[index]
        assert "tools" not in md.client._config_list[0]  # type: ignore[union-attr]

        with pytest.raises(ValueError) as e:
            md.update_tool_signature(_exec_python_tool_sig["function"]["name"], is_remove=True)  # type: ignore[index]
        assert "The agent config doesn't have tool" in str(e.value)

        md.update_tool_signature(_exec_python_tool_sig, is_remove=False)
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig]  # type: ignore[union-attr]

        # I guess this is fine, but it's not what I expected
        md.update_tool_signature("some_random_name", is_remove=True)  # type: ignore[arg-type]
        assert md.client._config_list[0]["tools"] == [_exec_python_tool_sig]  # type: ignore[union-attr]


_tool_response = {
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
        Tool Call Id: tool_1
        hello world

        Tool Call Id: tool_2
        goodbye and thanks for all the fish

        Tool Call Id: tool_3
        Error: Function multi_tool_call_echo not found.
        """
    ),
}


@pytest.mark.parametrize(
    "llm_config, messages, config, mock_response, expected_final, expected_retval",
    [
        (False, [], None, "", False, None),
        (
            {"cache_seed": None, "config_list": _config_list},
            [{"role": "user", "content": "1+1="}],
            None,
            "1+1=2",
            True,
            "2",
        ),
        (
            {"cache_seed": None, "config_list": _config_list},
            [_tool_response],
            None,
            "Good job with tool!",
            True,
            "Good job with tool!",
        ),
        (
            {"cache_seed": None, "config_list": _config_list},
            [_tool_response],
            None,
            "Good job with tool!",
            True,
            "Good job with tool!",
        ),
    ],
)
def test_generate_oai_reply_mocked_openai(
    llm_config: Union[Dict[str, Any], Literal[False]],
    messages: List[Dict[str, Any]],
    config: Optional[OpenAIWrapper],
    mock_response: str,
    expected_final: bool,
    expected_retval: str,
) -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        md = LLMMiddleware(name="agent1", llm_config=llm_config)

        with unittest.mock.patch("autogen.oai.client.OpenAIWrapper.create") as client_create_mock:
            choices = [CompletionChoice(text=mock_response, index=0, finish_reason="stop")]  # type: ignore[call-arg]
            completion = Completion(
                choices=choices, id="completion_id", created=0, model="model", object="text_completion"
            )
            client_create_mock.return_value = completion
            final, retval = md._generate_oai_reply(messages, config)
            assert final == expected_final
            if isinstance(retval, str):
                assert expected_retval in retval
            else:
                assert retval == expected_retval  # type: ignore[comparison-overlap]
            if llm_config is not False:
                client_create_mock.assert_called_once()
