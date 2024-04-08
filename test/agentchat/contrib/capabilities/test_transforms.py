import copy
from typing import Dict, List

import pytest

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


def test_MessageHistoryLimiter_apply_transform_long(message_history_limiter, long_messages):
    transformed_messages = message_history_limiter.apply_transform(long_messages)
    assert len(transformed_messages) == 3


def test_MessageHistoryLimiter_apply_transform_short(message_history_limiter, short_messages):
    transformed_messages = message_history_limiter.apply_transform(short_messages)
    assert len(transformed_messages) == 3


def test_MessageHistoryLimiter_get_stats_str_long(message_history_limiter, long_messages):
    pre_transform_messages = copy.deepcopy(long_messages)
    transformed_messages = message_history_limiter.apply_transform(long_messages)
    stats_str, had_effect = message_history_limiter.get_stats_str(pre_transform_messages, transformed_messages)
    assert had_effect
    assert stats_str == "Removed 2 messages. Number of messages reduced from 5 to 3."


def test_MessageHistoryLimiter_get_stats_str_short(message_history_limiter, short_messages):
    pre_transform_messages = copy.deepcopy(short_messages)
    transformed_messages = message_history_limiter.apply_transform(short_messages)
    stats_str, had_effect = message_history_limiter.get_stats_str(pre_transform_messages, transformed_messages)
    assert not had_effect
    assert stats_str == "No messages were removed."


# MessageTokenLimiter tests


def test_MessageTokenLimiter_apply_transform_long(message_token_limiter, long_messages):
    transformed_messages = message_token_limiter.apply_transform(long_messages)
    assert sum(_count_tokens(msg["content"]) for msg in transformed_messages) == 9


def test_MessageTokenLimiter_apply_transform_short(message_token_limiter, short_messages):
    transformed_messages = message_token_limiter.apply_transform(short_messages)
    assert sum(_count_tokens(msg["content"]) for msg in transformed_messages) == 3


def test_MessageTokenLimiter_get_stats_str_long(message_token_limiter, long_messages):
    pre_transform_messages = copy.deepcopy(long_messages)
    transformed_messages = message_token_limiter.apply_transform(long_messages)
    stats_str, had_effect = message_token_limiter.get_stats_str(pre_transform_messages, transformed_messages)
    assert had_effect
    assert stats_str == "Truncated 6 tokens. Number of tokens reduced from 15 to 9"


def test_MessageTokenLimiter_get_stats_str_short(message_token_limiter, short_messages):
    pre_transform_messages = copy.deepcopy(short_messages)
    transformed_messages = message_token_limiter.apply_transform(short_messages)
    stats_str, had_effect = message_token_limiter.get_stats_str(pre_transform_messages, transformed_messages)
    assert not had_effect
    assert stats_str == "No tokens were truncated."


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

    test_MessageHistoryLimiter_apply_transform_long(message_history_limiter, long_messages)
    test_MessageHistoryLimiter_apply_transform_short(message_history_limiter, short_messages)
    test_MessageHistoryLimiter_get_stats_str_long(message_history_limiter, long_messages)
    test_MessageHistoryLimiter_get_stats_str_short(message_history_limiter, short_messages)

    test_MessageTokenLimiter_apply_transform_long(message_token_limiter, long_messages)
    test_MessageTokenLimiter_apply_transform_short(message_token_limiter, short_messages)
    test_MessageTokenLimiter_get_stats_str_long(message_token_limiter, long_messages)
    test_MessageTokenLimiter_get_stats_str_short(message_token_limiter, short_messages)
