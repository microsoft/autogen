import copy
from typing import Dict, List

import pytest
from pytest_lazyfixture import lazy_fixture

from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter, MessageTokenLimiter, _count_tokens


@pytest.fixture
def long_messages() -> List[Dict]:
    return [
        {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
        {"role": "user", "content": "very very very very very very long string"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
    ]


@pytest.fixture
def short_messages() -> List[Dict]:
    return [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
    ]


@pytest.fixture
def message_history_limiter() -> MessageHistoryLimiter:
    return MessageHistoryLimiter(max_messages=3)


@pytest.fixture
def message_token_limiter() -> MessageTokenLimiter:
    return MessageTokenLimiter(max_tokens_per_message=3)


# MessageHistoryLimiter tests


@pytest.mark.parametrize(
    "messages, expected_len", [(lazy_fixture("long_messages"), 3), (lazy_fixture("short_messages"), 3)]
)
def test_message_history_limiter_apply_transform(message_history_limiter, messages, expected_len):
    transformed_messages = message_history_limiter.apply_transform(messages)
    assert len(transformed_messages) == expected_len


@pytest.mark.parametrize(
    "messages, expected_stats, expected_effect",
    [
        (lazy_fixture("long_messages"), "Removed 2 messages. Number of messages reduced from 5 to 3.", True),
        (lazy_fixture("short_messages"), "No messages were removed.", False),
    ],
)
def test_message_history_limiter_get_stats(message_history_limiter, messages, expected_stats, expected_effect):
    pre_transform_messages = copy.deepcopy(messages)
    transformed_messages = message_history_limiter.apply_transform(messages)
    stats_str, had_effect = message_history_limiter.get_stats(pre_transform_messages, transformed_messages)
    assert had_effect == expected_effect
    assert stats_str == expected_stats


# MessageTokenLimiter tests


@pytest.mark.parametrize(
    "messages, expected_token_count", [(lazy_fixture("long_messages"), 9), (lazy_fixture("short_messages"), 3)]
)
def test_message_token_limiter_apply_transform(message_token_limiter, messages, expected_token_count):
    transformed_messages = message_token_limiter.apply_transform(messages)
    assert sum(_count_tokens(msg["content"]) for msg in transformed_messages) == expected_token_count


@pytest.mark.parametrize(
    "messages, expected_stats, expected_effect",
    [
        (lazy_fixture("long_messages"), "Truncated 6 tokens. Number of tokens reduced from 15 to 9", True),
        (lazy_fixture("short_messages"), "No tokens were truncated.", False),
    ],
)
def test_message_token_limiter_get_stats(message_token_limiter, messages, expected_stats, expected_effect):
    pre_transform_messages = copy.deepcopy(messages)
    transformed_messages = message_token_limiter.apply_transform(messages)
    stats_str, had_effect = message_token_limiter.get_stats(pre_transform_messages, transformed_messages)
    assert had_effect == expected_effect
    assert stats_str == expected_stats


if __name__ == "__main__":
    long_messages = [
        {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
        {"role": "user", "content": "very very very very very very long string"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
    ]
    short_messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
        {"role": "user", "content": "how"},
    ]
    message_history_limiter = MessageHistoryLimiter(max_messages=3)
    message_token_limiter = MessageTokenLimiter(max_tokens_per_message=3)

    # Call the MessageHistoryLimiter tests
    test_message_history_limiter_apply_transform(message_history_limiter, long_messages, 3)
    test_message_history_limiter_apply_transform(message_history_limiter, short_messages, 3)
    test_message_history_limiter_get_stats(
        message_history_limiter, long_messages, "Removed 2 messages. Number of messages reduced from 5 to 3.", True
    )
    test_message_history_limiter_get_stats(message_history_limiter, short_messages, "No messages were removed.", False)

    # Call the MessageTokenLimiter tests
    test_message_token_limiter_apply_transform(message_token_limiter, long_messages, 9)
    test_message_token_limiter_apply_transform(message_token_limiter, short_messages, 3)
    test_message_token_limiter_get_stats(
        message_token_limiter, long_messages, "Truncated 6 tokens. Number of tokens reduced from 15 to 9", True
    )
    test_message_token_limiter_get_stats(message_token_limiter, short_messages, "No tokens were truncated.", False)
