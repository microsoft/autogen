import copy
import os
import sys
import tempfile
from typing import Any, Dict, List, Union

import pytest

import autogen
from autogen import token_count_utils
from autogen.agentchat.contrib.capabilities.transform_messages import TransformMessages
from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter, MessageTokenLimiter

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402


def _count_tokens(content: Union[str, List[Dict[str, Any]]]) -> int:
    token_count = 0
    if isinstance(content, str):
        token_count = token_count_utils.count_token(content)
    elif isinstance(content, list):
        for item in content:
            token_count += _count_tokens(item.get("text", ""))
    return token_count


def test_limit_token_transform():
    """
    Test the TokenLimitTransform capability.
    """

    messages = [
        {"role": "user", "content": "short string"},
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "very very very very very very very very long string"}],
        },
    ]

    # check if token limit per message is not exceeded.
    max_tokens_per_message = 5
    token_limit_transform = MessageTokenLimiter(max_tokens_per_message=max_tokens_per_message)
    transformed_messages = token_limit_transform.apply_transform(copy.deepcopy(messages))

    for message in transformed_messages:
        assert _count_tokens(message["content"]) <= max_tokens_per_message

    # check if total token limit is not exceeded.
    max_tokens = 10
    token_limit_transform = MessageTokenLimiter(max_tokens=max_tokens)
    transformed_messages = token_limit_transform.apply_transform(copy.deepcopy(messages))

    token_count = 0
    for message in transformed_messages:
        token_count += _count_tokens(message["content"])

    assert token_count <= max_tokens
    assert len(transformed_messages) <= len(messages)

    # check if token limit per message works nicely with total token limit.
    token_limit_transform = MessageTokenLimiter(max_tokens=max_tokens, max_tokens_per_message=max_tokens_per_message)

    transformed_messages = token_limit_transform.apply_transform(copy.deepcopy(messages))

    token_count = 0
    for message in transformed_messages:
        token_count_local = _count_tokens(message["content"])
        token_count += token_count_local
        assert token_count_local <= max_tokens_per_message

    assert token_count <= max_tokens
    assert len(transformed_messages) <= len(messages)


def test_max_message_history_length_transform():
    """
    Test the MessageHistoryLimiter capability to limit the number of messages.
    """
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
        {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
    ]

    max_messages = 2
    messages_limiter = MessageHistoryLimiter(max_messages=max_messages)
    transformed_messages = messages_limiter.apply_transform(copy.deepcopy(messages))

    assert len(transformed_messages) == max_messages
    assert transformed_messages == messages[max_messages:]


@pytest.mark.skipif(skip_openai, reason="Requested to skip openai test.")
def test_transform_messages_capability():
    """Test the TransformMessages capability to handle long contexts.

    This test is a replica of test_transform_chat_history_with_agents in test_context_handling.py
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        config_list = autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            KEY_LOC,
            filter_dict={
                "model": "gpt-3.5-turbo",
            },
        )

        assistant = autogen.AssistantAgent(
            "assistant", llm_config={"config_list": config_list}, max_consecutive_auto_reply=1
        )

        context_handling = TransformMessages(
            transforms=[
                MessageHistoryLimiter(max_messages=10),
                MessageTokenLimiter(max_tokens=10, max_tokens_per_message=5),
            ]
        )
        context_handling.add_to_agent(assistant)
        user = autogen.UserProxyAgent(
            "user",
            code_execution_config={"work_dir": temp_dir},
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
                assistant,
                message="Plot a chart of nvidia and tesla stock prices for the last 5 years",
                clear_history=False,
            )
        except Exception as e:
            assert False, f"Chat initiation failed with error {str(e)}"


if __name__ == "__main__":
    test_limit_token_transform()
    test_max_message_history_length_transform()
    test_transform_messages_capability()
