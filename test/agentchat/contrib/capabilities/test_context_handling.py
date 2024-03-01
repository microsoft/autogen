#!/usr/bin/env python3 -m pytest

import pytest
import os
import sys
import autogen
from autogen import token_count_utils
from autogen.agentchat.contrib.capabilities.context_handling import TransformChatHistory
from autogen import AssistantAgent, UserProxyAgent

# from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from test_assistant_agent import OAI_CONFIG_LIST, KEY_LOC  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai


def test_transform_chat_history():
    """
    Test the TransformChatHistory capability.

    In particular, test the following methods:
    - _transform_messages
    - truncate_string_to_tokens
    """
    messages = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "This is another test message"},
    ]

    # check whether num of messages is less than max_messages
    transform_chat_history = TransformChatHistory(max_messages=1)
    transformed_messages = transform_chat_history._transform_messages(messages)
    assert len(transformed_messages) == 2  # System message and the last message

    # check whether num of tokens per message are  is less than max_tokens
    transform_chat_history = TransformChatHistory(max_tokens_per_message=5)
    transformed_messages = transform_chat_history._transform_messages(messages)
    for message in transformed_messages:
        if message["role"] == "system":
            continue
        else:
            assert token_count_utils.count_token(message["content"]) <= 5

    transform_chat_history = TransformChatHistory(max_tokens=5)
    transformed_messages = transform_chat_history._transform_messages(messages)

    token_count = 0
    for message in transformed_messages:
        if message["role"] == "system":
            continue
        token_count += token_count_utils.count_token(message["content"])
    assert token_count <= 5


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
def test_transform_chat_history_with_agents():
    """
    This test create a GPT 3.5 agent with this capability and test the add_to_agent method.
    Including whether it prevents a crash when chat histories become excessively long.
    """
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        KEY_LOC,
        filter_dict={
            "model": "gpt-3.5-turbo",
        },
    )
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list}, max_consecutive_auto_reply=1)
    context_handling = TransformChatHistory(max_messages=10, max_tokens_per_message=5, max_tokens=1000)
    context_handling.add_to_agent(assistant)
    user = UserProxyAgent(
        "user",
        code_execution_config={"work_dir": "coding"},
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        max_consecutive_auto_reply=1,
    )

    # Create a very long chat history that is bound to cause a crash
    # for gpt 3.5
    for i in range(1000):
        assitant_msg = {"role": "assistant", "content": "test " * 1000}
        user_msg = {"role": "user", "content": ""}

        assistant.send(assitant_msg, user, request_reply=False)
        user.send(user_msg, assistant, request_reply=False)

    try:
        user.initiate_chat(
            assistant, message="Plot a chart of nvidia and tesla stock prices for the last 5 years", clear_history=False
        )
    except Exception as e:
        assert False, f"Chat initiation failed with error {str(e)}"


def test_transform_messages():
    """
    Test transform_messages_retain_order()
    """
    # Test case 1: Test that the order of messages is retained after transformation and Test that the messages are properly truncating.
    messages = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "Hi"},
        {"role": "user", "content": "user sending the 2nd test message"},
        {"role": "assistant", "content": "assistant sending the 3rd test message"},
        {"role": "assistant", "content": "assistant sending the 4th test message"},
    ]

    transform_chat_history = TransformChatHistory(max_messages=3, max_tokens_per_message=10, max_tokens=100)
    transformed_messages = transform_chat_history._transform_messages(messages)

    assert transformed_messages[0]["role"] == "system"
    assert transformed_messages[0]["content"] == "System message"
    assert transformed_messages[1]["role"] == "user"
    assert transformed_messages[1]["content"] == "user sending the 2nd test message"
    assert transformed_messages[2]["role"] == "assistant"
    assert transformed_messages[2]["content"] == "assistant sending the 3rd test message"
    assert transformed_messages[3]["role"] == "assistant"
    assert transformed_messages[3]["content"] == "assistant sending the 4th test message"

    # Test case 2: Test when no system message
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "user", "content": "user sending the 2nd test message"},
        {"role": "assistant", "content": "assistant sending the 3rd test message"},
        {"role": "assistant", "content": "assistant sending the 4th test message"},
    ]

    transform_chat_history = TransformChatHistory(max_messages=3, max_tokens_per_message=10, max_tokens=100)
    transformed_messages = transform_chat_history._transform_messages(messages)

    assert transformed_messages[0]["role"] == "user"
    assert transformed_messages[0]["content"] == "user sending the 2nd test message"
    assert transformed_messages[1]["role"] == "assistant"
    assert transformed_messages[1]["content"] == "assistant sending the 3rd test message"
    assert transformed_messages[2]["role"] == "assistant"
    assert transformed_messages[2]["content"] == "assistant sending the 4th test message"

    messages = [
        {"role": "user", "content": "Out of max messages"},
        {"role": "assistant", "content": "first second third fourth"},
        {"role": "user", "content": "a"},
    ]
    print(f"----Messages (N={len(messages)})----")
    orignal_tokens = 0
    for i, msg in enumerate(messages):
        print(f"[{msg['role']}-{i}]: {msg['content']}")
        tokens = token_count_utils.count_token(msg["content"])
        print("Number of tokens: ", tokens)
        orignal_tokens += tokens
    print("-----Total tokens: ", orignal_tokens, "-----")

    allowed_max_tokens = 2
    transform_chat_history = TransformChatHistory(max_messages=2, max_tokens=allowed_max_tokens)
    transformed_messages = transform_chat_history._transform_messages(messages)

    print("Max allowed tokens: ", allowed_max_tokens)

    print("Transformed contents")
    for msg in transformed_messages:
        print(msg["content"])
        print("Number of tokens: ", token_count_utils.count_token(msg["content"]))
    assert len(transformed_messages) == 1
    assert transformed_messages[0]["role"] == "user"


def test_truncate_str_to_tokens():
    """
    Test the truncate_str_to_tokens function.
    """
    from autogen.agentchat.contrib.capabilities.context_handling import truncate_str_to_tokens

    # Test case 1: Truncate string with fewer tokens than max_tokens
    text = "This is a test"
    max_tokens = 5
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert truncated_text == text

    # Test case 2: Truncate string with more tokens than max_tokens
    text = "This is a test"
    max_tokens = 3
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert truncated_text == "This is a"

    # Test case 3: Truncate empty string
    text = ""
    max_tokens = 5
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert truncated_text == ""

    # Test case 4: Truncate string with exact number of tokens as max_tokens
    text = "This is a test"
    max_tokens = 4
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert truncated_text == "This is a test"

    # Test case 5: Truncate string with no tokens found
    text = "This is a test"
    max_tokens = 0
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert truncated_text == ""

    # Test case 6: Truncate string when actual tokens are more than max_tokens
    text = "This is a test with a looooooonngggg word"
    max_tokens = 8
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    word_count = len(truncated_text.split())
    assert word_count <= max_tokens

    # Test case 7: Truncate string with exact number of tokens as max_tokens
    text = "This\nis\na test"
    max_tokens = 4
    truncated_text = truncate_str_to_tokens(text, max_tokens)
    assert "This\nis" in truncated_text


if __name__ == "__main__":
    test_transform_chat_history()
    test_transform_chat_history_with_agents()
    test_truncate_str_to_tokens()
    test_transform_messages()
