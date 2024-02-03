import pytest
import os
import sys
from autogen import token_count_utils
from autogen.agentchat.contrib.capabilities.context_handling import TransformChatHistory


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


if __name__ == "__main__":
    test_transform_chat_history()
