import json
from typing import Any, Callable, Dict, List

import pytest

from autogen.agentchat.conversable_agent import ConversableAgent


def _tool_func_1(arg1: str, arg2: str) -> str:
    return f"_tool_func_1: {arg1} {arg2}"


def _tool_func_2(arg1: str, arg2: str) -> str:
    return f"_tool_func_2: {arg1} {arg2}"


def _tool_func_error(arg1: str, arg2: str) -> str:
    raise RuntimeError("Error in tool function")


async def _a_tool_func_1(arg1: str, arg2: str) -> str:
    return f"_tool_func_1: {arg1} {arg2}"


async def _a_tool_func_2(arg1: str, arg2: str) -> str:
    return f"_tool_func_2: {arg1} {arg2}"


async def _a_tool_func_error(arg1: str, arg2: str) -> str:
    raise RuntimeError("Error in tool function")


_tool_use_message_1 = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "_tool_func_1",
                "arguments": json.dumps({"arg1": "value1", "arg2": "value2"}),
            },
        },
        {
            "id": "2",
            "type": "function",
            "function": {
                "name": "_tool_func_2",
                "arguments": json.dumps({"arg1": "value3", "arg2": "value4"}),
            },
        },
    ],
}

_tool_use_message_1_bad_json = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "_tool_func_1",
                # add extra comma to make json invalid
                "arguments": json.dumps({"arg1": "value3", "arg2": "value4"})[:-1] + ",}",
            },
        },
        {
            "id": "2",
            "type": "function",
            "function": {
                "name": "_tool_func_2",
                "arguments": json.dumps({"arg1": "value3", "arg2": "value4"}),
            },
        },
    ],
}

_tool_use_message_1_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {"tool_call_id": "1", "role": "tool", "content": "_tool_func_1: value1 value2"},
        {"tool_call_id": "2", "role": "tool", "content": "_tool_func_2: value3 value4"},
    ],
    # "content": "Tool Call Id: 1\n_tool_func_1: value1 value2\n\nTool Call Id: 2\n_tool_func_2: value3 value4",
    "content": "_tool_func_1: value1 value2\n\n_tool_func_2: value3 value4",
}


_tool_use_message_1_bad_json_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {
            "tool_call_id": "1",
            "role": "tool",
            "content": "Error: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n The argument must be in JSON format.",
        },
        {"tool_call_id": "2", "role": "tool", "content": "_tool_func_2: value3 value4"},
    ],
    "content": "Error: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n The argument must be in JSON format.\n\n_tool_func_2: value3 value4",
}

_tool_use_message_1_error_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {"tool_call_id": "1", "role": "tool", "content": "_tool_func_1: value1 value2"},
        {
            "tool_call_id": "2",
            "role": "tool",
            "content": "Error: Error in tool function",
        },
    ],
    "content": "_tool_func_1: value1 value2\n\nError: Error in tool function",
}

_tool_use_message_1_not_found_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {"tool_call_id": "1", "role": "tool", "content": "_tool_func_1: value1 value2"},
        {
            "tool_call_id": "2",
            "role": "tool",
            "content": "Error: Function _tool_func_2 not found.",
        },
    ],
    "content": "_tool_func_1: value1 value2\n\nError: Function _tool_func_2 not found.",
}

_function_use_message_1 = {
    "role": "assistant",
    "content": None,
    "function_call": {
        "name": "_tool_func_1",
        "arguments": json.dumps({"arg1": "value1", "arg2": "value2"}),
    },
}

_function_use_message_1_bad_json = {
    "role": "assistant",
    "content": None,
    "function_call": {
        "name": "_tool_func_1",
        "arguments": json.dumps({"arg1": "value1", "arg2": "value2"})[:-1] + ",}",
    },
}

_function_use_message_1_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "_tool_func_1: value1 value2",
}

_function_use_message_1_bad_json_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "Error: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n The argument must be in JSON format.",
}

_function_use_message_1_error_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "Error: Error in tool function",
}

_function_use_message_1_not_found_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "Error: Function _tool_func_1 not found.",
}

_text_message = {"content": "Hi!", "role": "user"}


def _get_function_map(is_function_async: bool, drop_tool_2: bool = False) -> Dict[str, Callable[..., Any]]:
    if is_function_async:
        return (
            {
                "_tool_func_1": _a_tool_func_1,
                "_tool_func_2": _a_tool_func_2,
            }
            if not drop_tool_2
            else {
                "_tool_func_1": _a_tool_func_1,
            }
        )
    else:
        return (
            {
                "_tool_func_1": _tool_func_1,
                "_tool_func_2": _tool_func_2,
            }
            if not drop_tool_2
            else {
                "_tool_func_1": _tool_func_1,
            }
        )


def _get_error_function_map(
    is_function_async: bool, error_on_tool_func_2: bool = True
) -> Dict[str, Callable[..., Any]]:
    if is_function_async:
        return {
            "_tool_func_1": _a_tool_func_1 if error_on_tool_func_2 else _a_tool_func_error,
            "_tool_func_2": _a_tool_func_error if error_on_tool_func_2 else _a_tool_func_2,
        }
    else:
        return {
            "_tool_func_1": _tool_func_1 if error_on_tool_func_2 else _tool_func_error,
            "_tool_func_2": _tool_func_error if error_on_tool_func_2 else _tool_func_2,
        }


@pytest.mark.parametrize("is_function_async", [True, False])
def test_generate_function_call_reply_on_function_call_message(is_function_async: bool) -> None:
    agent = ConversableAgent(name="agent", llm_config=False)

    # empty function_map
    agent._function_map = {}
    messages = [_function_use_message_1]
    finished, retval = agent.generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_not_found_expected_reply)

    # function map set
    agent._function_map = _get_function_map(is_function_async)

    # correct function call, multiple times to make sure cleanups are done properly
    for _ in range(3):
        messages = [_function_use_message_1]
        finished, retval = agent.generate_function_call_reply(messages)
        assert (finished, retval) == (True, _function_use_message_1_expected_reply)

    # bad JSON
    messages = [_function_use_message_1_bad_json]
    finished, retval = agent.generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_bad_json_expected_reply)

    # tool call
    messages = [_tool_use_message_1]
    finished, retval = agent.generate_function_call_reply(messages)
    assert (finished, retval) == (False, None)

    # text message
    messages: List[Dict[str, str]] = [_text_message]
    finished, retval = agent.generate_function_call_reply(messages)
    assert (finished, retval) == (False, None)

    # error in function (raises Exception)
    agent._function_map = _get_error_function_map(is_function_async, error_on_tool_func_2=False)
    messages = [_function_use_message_1]
    finished, retval = agent.generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_error_expected_reply)


@pytest.mark.asyncio()
@pytest.mark.parametrize("is_function_async", [True, False])
async def test_a_generate_function_call_reply_on_function_call_message(is_function_async: bool) -> None:
    agent = ConversableAgent(name="agent", llm_config=False)

    # empty function_map
    agent._function_map = {}
    messages = [_function_use_message_1]
    finished, retval = await agent.a_generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_not_found_expected_reply)

    # function map set
    agent._function_map = _get_function_map(is_function_async)

    # correct function call, multiple times to make sure cleanups are done properly
    for _ in range(3):
        messages = [_function_use_message_1]
        finished, retval = await agent.a_generate_function_call_reply(messages)
        assert (finished, retval) == (True, _function_use_message_1_expected_reply)

    # bad JSON
    messages = [_function_use_message_1_bad_json]
    finished, retval = await agent.a_generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_bad_json_expected_reply)

    # tool call
    messages = [_tool_use_message_1]
    finished, retval = await agent.a_generate_function_call_reply(messages)
    assert (finished, retval) == (False, None)

    # text message
    messages: List[Dict[str, str]] = [_text_message]
    finished, retval = await agent.a_generate_function_call_reply(messages)
    assert (finished, retval) == (False, None)

    # error in function (raises Exception)
    agent._function_map = _get_error_function_map(is_function_async, error_on_tool_func_2=False)
    messages = [_function_use_message_1]
    finished, retval = await agent.a_generate_function_call_reply(messages)
    assert (finished, retval) == (True, _function_use_message_1_error_expected_reply)


@pytest.mark.parametrize("is_function_async", [True, False])
def test_generate_tool_calls_reply_on_function_call_message(is_function_async: bool) -> None:
    agent = ConversableAgent(name="agent", llm_config=False)

    # empty function_map
    agent._function_map = _get_function_map(is_function_async, drop_tool_2=True)
    messages = [_tool_use_message_1]
    finished, retval = agent.generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_not_found_expected_reply)

    # function map set
    agent._function_map = _get_function_map(is_function_async)

    # correct function call, multiple times to make sure cleanups are done properly
    for _ in range(3):
        messages = [_tool_use_message_1]
        finished, retval = agent.generate_tool_calls_reply(messages)
        assert (finished, retval) == (True, _tool_use_message_1_expected_reply)

    # bad JSON
    messages = [_tool_use_message_1_bad_json]
    finished, retval = agent.generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_bad_json_expected_reply)

    # function call
    messages = [_function_use_message_1]
    finished, retval = agent.generate_tool_calls_reply(messages)
    assert (finished, retval) == (False, None)

    # text message
    messages: List[Dict[str, str]] = [_text_message]
    finished, retval = agent.generate_tool_calls_reply(messages)
    assert (finished, retval) == (False, None)

    # error in function (raises Exception)
    agent._function_map = _get_error_function_map(is_function_async)
    messages = [_tool_use_message_1]
    finished, retval = agent.generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_error_expected_reply)


@pytest.mark.asyncio()
@pytest.mark.parametrize("is_function_async", [True, False])
async def test_a_generate_tool_calls_reply_on_function_call_message(is_function_async: bool) -> None:
    agent = ConversableAgent(name="agent", llm_config=False)

    # empty function_map
    agent._function_map = _get_function_map(is_function_async, drop_tool_2=True)
    messages = [_tool_use_message_1]
    finished, retval = await agent.a_generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_not_found_expected_reply)

    # function map set
    agent._function_map = _get_function_map(is_function_async)

    # correct function call, multiple times to make sure cleanups are done properly
    for _ in range(3):
        messages = [_tool_use_message_1]
        finished, retval = await agent.a_generate_tool_calls_reply(messages)
        assert (finished, retval) == (True, _tool_use_message_1_expected_reply)

    # bad JSON
    messages = [_tool_use_message_1_bad_json]
    finished, retval = await agent.a_generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_bad_json_expected_reply)

    # function call
    messages = [_function_use_message_1]
    finished, retval = await agent.a_generate_tool_calls_reply(messages)
    assert (finished, retval) == (False, None)

    # text message
    messages: List[Dict[str, str]] = [_text_message]
    finished, retval = await agent.a_generate_tool_calls_reply(messages)
    assert (finished, retval) == (False, None)

    # error in function (raises Exception)
    agent._function_map = _get_error_function_map(is_function_async)
    messages = [_tool_use_message_1]
    finished, retval = await agent.a_generate_tool_calls_reply(messages)
    assert (finished, retval) == (True, _tool_use_message_1_error_expected_reply)
