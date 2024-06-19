#!/usr/bin/env python3 -m pytest

import pytest

import autogen
from autogen.oai.client_utils import should_hide_tools, validate_parameter


def test_validate_parameter():
    # Test valid parameters
    params = {
        "model": "Qwen/Qwen2-72B-Instruct",
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "top_k": 50,
        "repetition_penalty": 0.5,
        "presence_penalty": 1.5,
        "frequency_penalty": 1.5,
        "min_p": 0.2,
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }

    # Should return the original value as they are valid
    assert params["model"] == validate_parameter(params, "model", str, False, None, None, None)
    assert params["max_tokens"] == validate_parameter(params, "max_tokens", int, True, 512, (0, None), None)
    assert params["stream"] == validate_parameter(params, "stream", bool, False, False, None, None)
    assert params["temperature"] == validate_parameter(params, "temperature", (int, float), True, None, None, None)
    assert params["top_k"] == validate_parameter(params, "top_k", int, True, None, None, None)
    assert params["repetition_penalty"] == validate_parameter(
        params, "repetition_penalty", float, True, None, None, None
    )
    assert params["presence_penalty"] == validate_parameter(
        params, "presence_penalty", (int, float), True, None, (-2, 2), None
    )
    assert params["safety_model"] == validate_parameter(params, "safety_model", str, True, None, None, None)

    # Test None allowed
    params = {
        "max_tokens": None,
    }

    # Should remain None
    assert validate_parameter(params, "max_tokens", int, True, 512, (0, None), None) is None

    # Test not None allowed
    params = {
        "max_tokens": None,
    }

    # Should return default
    assert 512 == validate_parameter(params, "max_tokens", int, False, 512, (0, None), None)

    # Test invalid parameters
    params = {
        "stream": "Yes",
        "temperature": "0.5",
        "top_p": "0.8",
        "top_k": "50",
        "repetition_penalty": "0.5",
        "presence_penalty": "1.5",
        "frequency_penalty": "1.5",
        "min_p": "0.2",
        "safety_model": False,
    }

    # Should all be set to defaults
    assert validate_parameter(params, "stream", bool, False, False, None, None) is not None
    assert validate_parameter(params, "temperature", (int, float), True, None, None, None) is None
    assert validate_parameter(params, "top_p", (int, float), True, None, None, None) is None
    assert validate_parameter(params, "top_k", int, True, None, None, None) is None
    assert validate_parameter(params, "repetition_penalty", float, True, None, None, None) is None
    assert validate_parameter(params, "presence_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "frequency_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "min_p", (int, float), True, None, (0, 1), None) is None
    assert validate_parameter(params, "safety_model", str, True, None, None, None) is None

    # Test parameters outside of bounds
    params = {
        "max_tokens": -200,
        "presence_penalty": -5,
        "frequency_penalty": 5,
        "min_p": -0.5,
    }

    # Should all be set to defaults
    assert 512 == validate_parameter(params, "max_tokens", int, True, 512, (0, None), None)
    assert validate_parameter(params, "presence_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "frequency_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "min_p", (int, float), True, None, (0, 1), None) is None

    # Test valid list options
    params = {
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }

    # Should all be set to defaults
    assert "Meta-Llama/Llama-Guard-7b" == validate_parameter(
        params, "safety_model", str, True, None, None, ["Meta-Llama/Llama-Guard-7b", "Meta-Llama/Llama-Guard-13b"]
    )

    # Test invalid list options
    params = {
        "stream": True,
    }

    # Should all be set to defaults
    assert not validate_parameter(params, "stream", bool, False, False, None, [False])

    # test invalid type
    params = {
        "temperature": None,
    }

    # should be set to defaults
    assert validate_parameter(params, "temperature", (int, float), False, 0.7, (0.0, 1.0), None) == 0.7

    # test value out of bounds
    params = {
        "temperature": 23,
    }

    # should be set to defaults
    assert validate_parameter(params, "temperature", (int, float), False, 1.0, (0.0, 1.0), None) == 1.0

    # type error for the parameters
    with pytest.raises(TypeError):
        validate_parameter({}, "param", str, True, None, None, "not_a_list")

    # passing empty params, which will set to defaults
    assert validate_parameter({}, "max_tokens", int, True, 512, (0, None), None) == 512


def test_should_hide_tools():
    # Test messages
    no_tools_called_messages = [
        {"content": "You are a chess program and are playing for player white.", "role": "system"},
        {"content": "Let's play chess! Make a move.", "role": "user"},
        {
            "tool_calls": [
                {
                    "id": "call_abcde56o5jlugh9uekgo84c6",
                    "function": {"arguments": "{}", "name": "get_legal_moves"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {
            "tool_calls": [
                {
                    "id": "call_p1fla56o5jlugh9uekgo84c6",
                    "function": {"arguments": "{}", "name": "get_legal_moves"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {
            "tool_calls": [
                {
                    "id": "call_lcow1j0ehuhrcr3aakdmd9ju",
                    "function": {"arguments": '{"move":"g1f3"}', "name": "make_move"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
    ]
    one_tool_called_messages = [
        {"content": "You are a chess program and are playing for player white.", "role": "system"},
        {"content": "Let's play chess! Make a move.", "role": "user"},
        {
            "tool_calls": [
                {
                    "id": "call_abcde56o5jlugh9uekgo84c6",
                    "function": {"arguments": "{}", "name": "get_legal_moves"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {
            "tool_call_id": "call_abcde56o5jlugh9uekgo84c6",
            "role": "user",
            "content": "Possible moves are: g1h3,g1f3,b1c3,b1a3,h2h3,g2g3,f2f3,e2e3,d2d3,c2c3,b2b3,a2a3,h2h4,g2g4,f2f4,e2e4,d2d4,c2c4,b2b4,a2a4",
        },
        {
            "tool_calls": [
                {
                    "id": "call_lcow1j0ehuhrcr3aakdmd9ju",
                    "function": {"arguments": '{"move":"g1f3"}', "name": "make_move"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
    ]
    messages = [
        {"content": "You are a chess program and are playing for player white.", "role": "system"},
        {"content": "Let's play chess! Make a move.", "role": "user"},
        {
            "tool_calls": [
                {
                    "id": "call_abcde56o5jlugh9uekgo84c6",
                    "function": {"arguments": "{}", "name": "get_legal_moves"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {
            "tool_call_id": "call_abcde56o5jlugh9uekgo84c6",
            "role": "user",
            "content": "Possible moves are: g1h3,g1f3,b1c3,b1a3,h2h3,g2g3,f2f3,e2e3,d2d3,c2c3,b2b3,a2a3,h2h4,g2g4,f2f4,e2e4,d2d4,c2c4,b2b4,a2a4",
        },
        {
            "tool_calls": [
                {
                    "id": "call_p1fla56o5jlugh9uekgo84c6",
                    "function": {"arguments": "{}", "name": "get_legal_moves"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {
            "tool_call_id": "call_p1fla56o5jlugh9uekgo84c6",
            "role": "user",
            "content": "Possible moves are: g1h3,g1f3,b1c3,b1a3,h2h3,g2g3,f2f3,e2e3,d2d3,c2c3,b2b3,a2a3,h2h4,g2g4,f2f4,e2e4,d2d4,c2c4,b2b4,a2a4",
        },
        {
            "tool_calls": [
                {
                    "id": "call_lcow1j0ehuhrcr3aakdmd9ju",
                    "function": {"arguments": '{"move":"g1f3"}', "name": "make_move"},
                    "type": "function",
                }
            ],
            "content": None,
            "role": "assistant",
        },
        {"tool_call_id": "call_lcow1j0ehuhrcr3aakdmd9ju", "role": "user", "content": "Moved knight (♘) from g1 to f3."},
    ]

    # Test if no tools
    no_tools = []
    all_tools = [
        {
            "type": "function",
            "function": {
                "description": "Call this tool to make a move after you have the list of legal moves.",
                "name": "make_move",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "move": {"type": "string", "description": "A move in UCI format. (e.g. e2e4 or e7e5 or e7e8q)"}
                    },
                    "required": ["move"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "description": "Call this tool to make a move after you have the list of legal moves.",
                "name": "get_legal_moves",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]

    # Should not hide for any hide_tools value
    assert not should_hide_tools(messages, no_tools, "if_all_run")
    assert not should_hide_tools(messages, no_tools, "if_any_run")
    assert not should_hide_tools(messages, no_tools, "never")

    # Has run tools but never hide, should be false
    assert not should_hide_tools(messages, all_tools, "never")

    # Has run tools, should be true if all or any
    assert should_hide_tools(messages, all_tools, "if_all_run")
    assert should_hide_tools(messages, all_tools, "if_any_run")

    # Hasn't run any tools, should be false for all
    assert not should_hide_tools(no_tools_called_messages, all_tools, "if_all_run")
    assert not should_hide_tools(no_tools_called_messages, all_tools, "if_any_run")
    assert not should_hide_tools(no_tools_called_messages, all_tools, "never")

    # Has run one of the two tools, should be true only for 'if_any_run'
    assert not should_hide_tools(one_tool_called_messages, all_tools, "if_all_run")
    assert should_hide_tools(one_tool_called_messages, all_tools, "if_any_run")
    assert not should_hide_tools(one_tool_called_messages, all_tools, "never")

    # Parameter validation
    with pytest.raises(TypeError):
        assert not should_hide_tools(one_tool_called_messages, all_tools, "not_a_valid_value")


if __name__ == "__main__":
    # test_validate_parameter()
    test_should_hide_tools()
