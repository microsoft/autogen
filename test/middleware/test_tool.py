import json
import pytest

from autogen.middleware.tool import ToolUseMiddleware


def _tool_func_1(arg1: str, arg2: str) -> str:
    return f"_tool_func_1: {arg1} {arg2}"


def _tool_func_2(arg1: str, arg2: str) -> str:
    return f"_tool_func_2: {arg1} {arg2}"


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

_tool_use_message_1_expected_reply = {
    "role": "tool",
    "tool_responses": [
        {"tool_call_id": "1", "role": "tool", "content": "_tool_func_1: value1 value2"},
        {"tool_call_id": "2", "role": "tool", "content": "_tool_func_2: value3 value4"},
    ],
    "content": "Tool Call Id: 1\n_tool_func_1: value1 value2\n\nTool Call Id: 2\n_tool_func_2: value3 value4",
}

_function_use_message_1 = {
    "role": "assistant",
    "content": None,
    "function_call": {
        "name": "_tool_func_1",
        "arguments": json.dumps({"arg1": "value1", "arg2": "value2"}),
    },
}

_function_use_message_1_expected_reply = {
    "name": "_tool_func_1",
    "role": "function",
    "content": "_tool_func_1: value1 value2",
}


def test_tool_use() -> None:
    md = ToolUseMiddleware(
        function_map={
            "_tool_func_1": _tool_func_1,
            "_tool_func_2": _tool_func_2,
        }
    )
    messages = [_tool_use_message_1]
    reply = md.call(messages)
    assert reply == _tool_use_message_1_expected_reply


@pytest.mark.asyncio()
async def test_tool_use_async() -> None:
    md = ToolUseMiddleware(
        function_map={
            "_tool_func_1": _tool_func_1,
            "_tool_func_2": _tool_func_2,
        }
    )
    messages = [_tool_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _tool_use_message_1_expected_reply


def test_function_use() -> None:
    md = ToolUseMiddleware(
        function_map={
            "_tool_func_1": _tool_func_1,
            "_tool_func_2": _tool_func_2,
        }
    )
    messages = [_function_use_message_1]
    reply = md.call(messages)
    assert reply == _function_use_message_1_expected_reply


@pytest.mark.asyncio()
async def test_function_use_async() -> None:
    md = ToolUseMiddleware(
        function_map={
            "_tool_func_1": _tool_func_1,
            "_tool_func_2": _tool_func_2,
        }
    )
    messages = [_function_use_message_1]
    reply = await md.a_call(messages)
    assert reply == _function_use_message_1_expected_reply
