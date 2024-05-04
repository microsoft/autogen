import copy
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter, MessageTokenLimiter, _count_tokens


def get_long_messages() -> List[Dict]:
    return [
        {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
        {"role": "user", "content": "very very very very very very long string"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
    ]


def get_short_messages() -> List[Dict]:
    return [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how are you"},
    ]


def get_no_content_messages() -> List[Dict]:
    return [{"role": "user", "function_call": "example"}, {"role": "assistant", "content": None}]


@pytest.fixture
def message_history_limiter() -> MessageHistoryLimiter:
    return MessageHistoryLimiter(max_messages=3)


@pytest.fixture
def message_token_limiter() -> MessageTokenLimiter:
    return MessageTokenLimiter(max_tokens_per_message=3)


@pytest.fixture
def message_token_limiter_with_threshold() -> MessageTokenLimiter:
    return MessageTokenLimiter(max_tokens_per_message=1, min_tokens=10)


# MessageHistoryLimiter


@pytest.mark.parametrize(
    "messages, expected_messages_len",
    [(get_long_messages(), 3), (get_short_messages(), 3), (get_no_content_messages(), 2)],
)
def test_message_history_limiter_apply_transform(message_history_limiter, messages, expected_messages_len):
    transformed_messages = message_history_limiter.apply_transform(messages)
    assert len(transformed_messages) == expected_messages_len


@pytest.mark.parametrize(
    "messages, expected_logs, expected_effect",
    [
        (get_long_messages(), "Removed 2 messages. Number of messages reduced from 5 to 3.", True),
        (get_short_messages(), "No messages were removed.", False),
        (get_no_content_messages(), "No messages were removed.", False),
    ],
)
def test_message_history_limiter_get_logs(message_history_limiter, messages, expected_logs, expected_effect):
    pre_transform_messages = copy.deepcopy(messages)
    transformed_messages = message_history_limiter.apply_transform(messages)
    logs_str, had_effect = message_history_limiter.get_logs(pre_transform_messages, transformed_messages)
    assert had_effect == expected_effect
    assert logs_str == expected_logs


# MessageTokenLimiter tests


@pytest.mark.parametrize(
    "messages, expected_token_count, expected_messages_len",
    [(get_long_messages(), 9, 5), (get_short_messages(), 5, 3), (get_no_content_messages(), 0, 2)],
)
def test_message_token_limiter_apply_transform(
    message_token_limiter, messages, expected_token_count, expected_messages_len
):
    transformed_messages = message_token_limiter.apply_transform(messages)
    assert (
        sum(_count_tokens(msg["content"]) for msg in transformed_messages if "content" in msg) == expected_token_count
    )
    assert len(transformed_messages) == expected_messages_len


@pytest.mark.parametrize(
    "messages, expected_token_count, expected_messages_len",
    [(get_long_messages(), 5, 5), (get_short_messages(), 5, 3), (get_no_content_messages(), 0, 2)],
)
def test_message_token_limiter_with_threshold_apply_transform(
    message_token_limiter_with_threshold, messages, expected_token_count, expected_messages_len
):
    transformed_messages = message_token_limiter_with_threshold.apply_transform(messages)
    assert (
        sum(_count_tokens(msg["content"]) for msg in transformed_messages if "content" in msg) == expected_token_count
    )
    assert len(transformed_messages) == expected_messages_len


@pytest.mark.parametrize(
    "messages, expected_logs, expected_effect",
    [
        (get_long_messages(), "Truncated 6 tokens. Number of tokens reduced from 15 to 9", True),
        (get_short_messages(), "No tokens were truncated.", False),
        (get_no_content_messages(), "No tokens were truncated.", False),
    ],
)
def test_message_token_limiter_get_logs(message_token_limiter, messages, expected_logs, expected_effect):
    pre_transform_messages = copy.deepcopy(messages)
    transformed_messages = message_token_limiter.apply_transform(messages)
    logs_str, had_effect = message_token_limiter.get_logs(pre_transform_messages, transformed_messages)
    assert had_effect == expected_effect
    assert logs_str == expected_logs


def test_text_compression():
    """Test the TextMessageCompressor transform."""
    try:
        from autogen.agentchat.contrib.capabilities.transforms import TextMessageCompressor

        text_compressor = TextMessageCompressor()
    except ImportError:
        pytest.skip("LLM Lingua is not installed.")

    text = "Run this test with a long string. "
    messages = [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "".join([text] * 3)}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "".join([text] * 3)}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "".join([text] * 3)}],
        },
    ]

    transformed_messages = text_compressor.apply_transform([{"content": text}])

    assert len(transformed_messages[0]["content"]) < len(text)

    # Test compressing all messages
    text_compressor = TextMessageCompressor()
    transformed_messages = text_compressor.apply_transform(copy.deepcopy(messages))
    for message in transformed_messages:
        assert len(message["content"][0]["text"]) < len(messages[0]["content"][0]["text"])


def test_text_compression_cache():
    try:
        from autogen.agentchat.contrib.capabilities.transforms import TextMessageCompressor

    except ImportError:
        pytest.skip("LLM Lingua is not installed.")

    messages = get_long_messages()
    mock_compressed_content = (1, {"content": "mock"})

    with patch(
        "autogen.agentchat.contrib.capabilities.transforms.TextMessageCompressor._cache_get",
        MagicMock(return_value=(1, {"content": "mock"})),
    ) as mocked_get, patch(
        "autogen.agentchat.contrib.capabilities.transforms.TextMessageCompressor._cache_set", MagicMock()
    ) as mocked_set:
        text_compressor = TextMessageCompressor()

        text_compressor.apply_transform(messages)
        text_compressor.apply_transform(messages)

        assert mocked_get.call_count == len(messages)
        assert mocked_set.call_count == len(messages)

    # We already populated the cache with the mock content
    # We need to test if we retrieve the correct content
    text_compressor = TextMessageCompressor()
    compressed_messages = text_compressor.apply_transform(messages)

    for message in compressed_messages:
        assert message["content"] == mock_compressed_content[1]


if __name__ == "__main__":
    long_messages = get_long_messages()
    short_messages = get_short_messages()
    no_content_messages = get_no_content_messages()
    msg_history_limiter = MessageHistoryLimiter(max_messages=3)
    msg_token_limiter = MessageTokenLimiter(max_tokens_per_message=3)
    msg_token_limiter_with_threshold = MessageTokenLimiter(max_tokens_per_message=1, min_tokens=10)

    # Test Parameters
    message_history_limiter_apply_transform_parameters = {
        "messages": [long_messages, short_messages, no_content_messages],
        "expected_messages_len": [3, 3, 2],
    }

    message_history_limiter_get_logs_parameters = {
        "messages": [long_messages, short_messages, no_content_messages],
        "expected_logs": [
            "Removed 2 messages. Number of messages reduced from 5 to 3.",
            "No messages were removed.",
            "No messages were removed.",
        ],
        "expected_effect": [True, False, False],
    }

    message_token_limiter_apply_transform_parameters = {
        "messages": [long_messages, short_messages, no_content_messages],
        "expected_token_count": [9, 5, 0],
        "expected_messages_len": [5, 3, 2],
    }

    message_token_limiter_with_threshold_apply_transform_parameters = {
        "messages": [long_messages, short_messages, no_content_messages],
        "expected_token_count": [5, 5, 0],
        "expected_messages_len": [5, 3, 2],
    }

    message_token_limiter_get_logs_parameters = {
        "messages": [long_messages, short_messages, no_content_messages],
        "expected_logs": [
            "Truncated 6 tokens. Number of tokens reduced from 15 to 9",
            "No tokens were truncated.",
            "No tokens were truncated.",
        ],
        "expected_effect": [True, False, False],
    }

    # Call the MessageHistoryLimiter tests

    for messages, expected_messages_len in zip(
        message_history_limiter_apply_transform_parameters["messages"],
        message_history_limiter_apply_transform_parameters["expected_messages_len"],
    ):
        test_message_history_limiter_apply_transform(msg_history_limiter, messages, expected_messages_len)

    for messages, expected_logs, expected_effect in zip(
        message_history_limiter_get_logs_parameters["messages"],
        message_history_limiter_get_logs_parameters["expected_logs"],
        message_history_limiter_get_logs_parameters["expected_effect"],
    ):
        test_message_history_limiter_get_logs(msg_history_limiter, messages, expected_logs, expected_effect)

    # Call the MessageTokenLimiter tests

    for messages, expected_token_count, expected_messages_len in zip(
        message_token_limiter_apply_transform_parameters["messages"],
        message_token_limiter_apply_transform_parameters["expected_token_count"],
        message_token_limiter_apply_transform_parameters["expected_messages_len"],
    ):
        test_message_token_limiter_apply_transform(
            msg_token_limiter, messages, expected_token_count, expected_messages_len
        )

    for messages, expected_token_count, expected_messages_len in zip(
        message_token_limiter_with_threshold_apply_transform_parameters["messages"],
        message_token_limiter_with_threshold_apply_transform_parameters["expected_token_count"],
        message_token_limiter_with_threshold_apply_transform_parameters["expected_messages_len"],
    ):
        test_message_token_limiter_with_threshold_apply_transform(
            msg_token_limiter_with_threshold, messages, expected_token_count, expected_messages_len
        )

    for messages, expected_logs, expected_effect in zip(
        message_token_limiter_get_logs_parameters["messages"],
        message_token_limiter_get_logs_parameters["expected_logs"],
        message_token_limiter_get_logs_parameters["expected_effect"],
    ):
        test_message_token_limiter_get_logs(msg_token_limiter, messages, expected_logs, expected_effect)
