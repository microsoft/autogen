import json
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from autogen.agentchat.agent import Agent
from autogen.agentchat.middleware.tool_use import ToolUseMiddleware


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
    "content": "Tool Call Id: 1\n_tool_func_1: value1 value2\n\nTool Call Id: 2\n_tool_func_2: value3 value4",
}


_tool_use_message_1_bad_json_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {
            "tool_call_id": "1",
            "role": "tool",
            "content": "Error: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n You argument should follow json format.",
        },
        {"tool_call_id": "2", "role": "tool", "content": "_tool_func_2: value3 value4"},
    ],
    "content": "Tool Call Id: 1\nError: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n You argument should follow json format.\n\nTool Call Id: 2\n_tool_func_2: value3 value4",
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
    "content": "Tool Call Id: 1\n_tool_func_1: value1 value2\n\nTool Call Id: 2\nError: Error in tool function",
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
    "content": "Tool Call Id: 1\n_tool_func_1: value1 value2\n\nTool Call Id: 2\nError: Function _tool_func_2 not found.",
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
    "content": "Error: Expecting property name enclosed in double quotes: line 1 column 37 (char 36)\n You argument should follow json format.",
}

_function_use_message_1_error_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "Error: Error in tool function",
}

_text_message = {"content": "Hi!", "role": "user"}


def _get_function_map(is_function_async: bool) -> Dict[str, Callable[..., Any]]:
    if is_function_async:
        return {
            "_tool_func_1": _a_tool_func_1,
            "_tool_func_2": _a_tool_func_2,
        }
    else:
        return {
            "_tool_func_1": _tool_func_1,
            "_tool_func_2": _tool_func_2,
        }


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


def test_init() -> None:
    md = ToolUseMiddleware(
        function_map={
            "tool_func_1": _tool_func_1,
            "tool_func_2": _tool_func_2,
        }
    )
    assert md.function_map == {
        "tool_func_1": _tool_func_1,
        "tool_func_2": _tool_func_2,
    }

    md = ToolUseMiddleware(function_map={})
    assert md.function_map == {}

    md = ToolUseMiddleware(None)
    assert md.function_map == {}

    with pytest.raises(ValueError) as e:
        md = ToolUseMiddleware({"my.name": _tool_func_1})
    assert str(e.value) == "Invalid name: my.name. Only letters, numbers, '_' and '-' are allowed."

    with pytest.raises(ValueError) as e:
        name = "my_name-" + "a" * 64
        md = ToolUseMiddleware({name: _tool_func_1})
    assert str(e.value) == f"Invalid name: {name}. Name must be less than 64 characters."


@pytest.mark.parametrize("is_function_async", [True, False])
def test_sync_text_message(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_function_map(is_function_async))
    next_mock = MagicMock()

    def next(
        messages: List[Dict[str, Any]],
        sender: Optional[Agent] = None,
    ) -> Dict[str, Any]:
        next_mock(messages, sender)
        return {"content": "Hello", "role": "assistant"}

    messages: List[Dict[str, str]] = [_text_message]
    reply = md.call(messages, next=next)
    next_mock.assert_called_once_with(messages, None)
    assert reply == {"content": "Hello", "role": "assistant"}


@pytest.mark.asyncio()
@pytest.mark.parametrize("is_function_async", [True, False])
async def test_async_text_message(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_function_map(is_function_async))
    next_mock = AsyncMock()

    async def next(
        messages: List[Dict[str, Any]],
        sender: Optional[Agent] = None,
    ) -> Dict[str, Any]:
        await next_mock(messages, sender)
        return {"content": "Hello", "role": "assistant"}

    messages = [_text_message]
    reply = await md.a_call(messages, next=next)
    next_mock.assert_awaited_once_with(messages, None)
    assert reply == {"content": "Hello", "role": "assistant"}


@pytest.mark.parametrize("is_function_async", [True, False])
def test_tool_use_from_sync(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_function_map(is_function_async))
    messages = [_tool_use_message_1]
    reply = md.call(messages)
    assert reply == _tool_use_message_1_expected_reply

    messages = [_tool_use_message_1_bad_json]
    reply = md.call(messages)
    assert reply == _tool_use_message_1_bad_json_expected_reply

    md = ToolUseMiddleware(_get_error_function_map(is_function_async))
    messages = [_tool_use_message_1]
    reply = md.call(messages)
    assert reply == _tool_use_message_1_error_expected_reply


@pytest.mark.parametrize("is_function_async", [True, False])
@pytest.mark.asyncio()
async def test_tool_use_from_async(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_function_map(is_function_async))
    messages = [_tool_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _tool_use_message_1_expected_reply

    messages = [_tool_use_message_1_bad_json]
    reply = await md.a_call(messages)
    assert reply == _tool_use_message_1_bad_json_expected_reply

    md = ToolUseMiddleware(_get_error_function_map(is_function_async))
    messages = [_tool_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _tool_use_message_1_error_expected_reply


@pytest.mark.parametrize("is_function_async", [True, False])
def test_tool_use_missing_functions_sync(is_function_async: bool) -> None:
    md = ToolUseMiddleware(
        {
            "_tool_func_1": _a_tool_func_1,
        }
        if is_function_async
        else {
            "_tool_func_1": _tool_func_1,
        }
    )
    messages = [_tool_use_message_1]
    reply = md.call(messages)
    assert reply == _tool_use_message_1_not_found_expected_reply


@pytest.mark.asyncio()
@pytest.mark.parametrize("is_function_async", [True, False])
async def test_tool_use_missing_functions_async(is_function_async: bool) -> None:
    md = ToolUseMiddleware(
        {
            "_tool_func_1": _a_tool_func_1,
        }
        if is_function_async
        else {
            "_tool_func_1": _tool_func_1,
        }
    )
    messages = [_tool_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _tool_use_message_1_not_found_expected_reply


@pytest.mark.parametrize("is_function_async", [True, False])
def test_sync_function(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_function_map(is_function_async))
    messages = [_function_use_message_1]
    reply = md.call(messages)
    assert reply == _function_use_message_1_expected_reply

    messages = [_function_use_message_1_bad_json]
    reply = md.call(messages)
    assert reply == _function_use_message_1_bad_json_expected_reply

    md = ToolUseMiddleware(_get_error_function_map(is_function_async, error_on_tool_func_2=False))
    messages = [_function_use_message_1]
    reply = md.call(messages)
    assert reply == _function_use_message_1_error_expected_reply


@pytest.mark.parametrize("is_function_async", [True, False])
@pytest.mark.asyncio()
async def test_async_function(is_function_async: bool) -> None:
    md = ToolUseMiddleware(_get_error_function_map(is_function_async))
    messages = [_function_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _function_use_message_1_expected_reply

    messages = [_function_use_message_1_bad_json]
    reply = await md.a_call(messages)
    assert reply == _function_use_message_1_bad_json_expected_reply

    md = ToolUseMiddleware(_get_error_function_map(is_function_async, error_on_tool_func_2=False))
    messages = [_function_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _function_use_message_1_error_expected_reply


def test_register_function() -> None:
    md = ToolUseMiddleware()

    md.register_function({"_tool_func_1": _tool_func_1})
    assert md.function_map == {"_tool_func_1": _tool_func_1}

    with pytest.raises(ValueError) as e:
        md.register_function({"my.name": _tool_func_1})
    assert str(e.value) == "Invalid name: my.name. Only letters, numbers, '_' and '-' are allowed."


def test_can_execute_function() -> None:
    md = ToolUseMiddleware(
        function_map={
            "_tool_func_1": _a_tool_func_1,
            "_tool_func_2": _a_tool_func_2,
        }
    )

    assert md.can_execute_function([])
    assert md.can_execute_function("_tool_func_1")
    assert md.can_execute_function(["_tool_func_1"])
    assert md.can_execute_function(["_tool_func_1", "_tool_func_2"])
    assert not md.can_execute_function("_tool_func_3")
    assert not md.can_execute_function(["_tool_func_3"])
    assert not md.can_execute_function(["_tool_func_1", "_tool_func_3"])
    assert not md.can_execute_function(["_tool_func_3", "_tool_func_4"])


def test__format_json_str() -> None:
    actual = ToolUseMiddleware._format_json_str(
        """{\n"tool": "python",\n"query": "print('hello')\nprint('world')"\n}"""
    )
    expected = """{"tool": "python","query": "print(\'hello\')\\nprint(\'world\')"}"""
    assert actual == expected

    actual = ToolUseMiddleware._format_json_str("""{\n  "location": "Boston, MA"\n}""")
    expected = """{  "location": "Boston, MA"}"""
    assert actual == expected

    actual = ToolUseMiddleware._format_json_str("""{"args": "a\na\na\ta"}""")
    expected = """{"args": "a\\na\\na\\ta"}"""
    assert actual == expected
