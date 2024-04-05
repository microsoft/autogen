#!/usr/bin/env python3 -m pytest

import pytest

from autogen.token_count_utils import (
    count_token,
    get_max_token_limit,
    num_tokens_from_functions,
    percentile_used,
    token_left,
)

func1 = {
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
func2 = {
    "name": "query_wolfram",
    "description": "Return the API query result from the Wolfram Alpha. the return is a tuple of (result, is_success).",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}
func3 = {
    "name": "python",
    "description": "run cell in ipython and return the execution result.",
    "parameters": {
        "type": "object",
        "properties": {
            "cell": {
                "type": "string",
                "description": "Valid Python cell to execute.",
            }
        },
        "required": ["cell"],
    },
}


@pytest.mark.parametrize(
    "input_functions, expected_count", [([func1], 44), ([func2], 46), ([func3], 45), ([func1, func2], 78)]
)
def test_num_tokens_from_functions(input_functions, expected_count):
    assert num_tokens_from_functions(input_functions) == expected_count


def test_count_token():
    messages = [
        {
            "role": "system",
            "content": "you are a helpful assistant. af3758 *3 33(3)",
        },
        {
            "role": "user",
            "content": "hello asdfjj qeweee",
        },
    ]
    assert count_token(messages) == 34
    assert percentile_used(messages) == 34 / 4096
    assert token_left(messages) == 4096 - 34

    text = "I'm sorry, but I'm not able to"
    assert count_token(text) == 10
    assert token_left(text) == 4096 - 10
    assert percentile_used(text) == 10 / 4096


def test_model_aliases():
    assert get_max_token_limit("gpt35-turbo") == get_max_token_limit("gpt-3.5-turbo")
    assert get_max_token_limit("gpt-35-turbo") == get_max_token_limit("gpt-3.5-turbo")
    assert get_max_token_limit("gpt4") == get_max_token_limit("gpt-4")
    assert get_max_token_limit("gpt4-32k") == get_max_token_limit("gpt-4-32k")


if __name__ == "__main__":
    #    test_num_tokens_from_functions()
    #    test_count_token()
    test_model_aliases()
