import copy
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from autogen.agentchat.contrib.capabilities.text_compressors import TextCompressor
from autogen.agentchat.contrib.capabilities.transforms import (
    MessageHistoryLimiter,
    MessageTokenLimiter,
    TextMessageCompressor,
    TextMessageContentName,
)
from autogen.agentchat.contrib.capabilities.transforms_util import count_text_tokens


class _MockTextCompressor:
    def compress_text(self, text: str, **compression_params) -> Dict[str, Any]:
        return {"compressed_prompt": ""}


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


def get_tool_messages() -> List[Dict]:
    return [
        {"role": "user", "content": "hello"},
        {"role": "tool_calls", "content": "calling_tool"},
        {"role": "tool", "content": "tool_response"},
        {"role": "user", "content": "how are you"},
        {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
    ]


def get_tool_messages_kept() -> List[Dict]:
    return [
        {"role": "user", "content": "hello"},
        {"role": "tool_calls", "content": "calling_tool"},
        {"role": "tool", "content": "tool_response"},
        {"role": "tool_calls", "content": "calling_tool"},
        {"role": "tool", "content": "tool_response"},
    ]


def get_messages_with_names() -> List[Dict]:
    return [
        {"role": "system", "content": "I am the system."},
        {"role": "user", "name": "charlie", "content": "I think the sky is blue."},
        {"role": "user", "name": "mary", "content": "The sky is red."},
        {"role": "user", "name": "bob", "content": "The sky is crimson."},
    ]


def get_messages_with_names_post_start() -> List[Dict]:
    return [
        {"role": "system", "content": "I am the system."},
        {"role": "user", "name": "charlie", "content": "'charlie' said:\nI think the sky is blue."},
        {"role": "user", "name": "mary", "content": "'mary' said:\nThe sky is red."},
        {"role": "user", "name": "bob", "content": "'bob' said:\nThe sky is crimson."},
    ]


def get_messages_with_names_post_end() -> List[Dict]:
    return [
        {"role": "system", "content": "I am the system."},
        {"role": "user", "name": "charlie", "content": "I think the sky is blue.\n(said 'charlie')"},
        {"role": "user", "name": "mary", "content": "The sky is red.\n(said 'mary')"},
        {"role": "user", "name": "bob", "content": "The sky is crimson.\n(said 'bob')"},
    ]


def get_messages_with_names_post_filtered() -> List[Dict]:
    return [
        {"role": "system", "content": "I am the system."},
        {"role": "user", "name": "charlie", "content": "I think the sky is blue."},
        {"role": "user", "name": "mary", "content": "'mary' said:\nThe sky is red."},
        {"role": "user", "name": "bob", "content": "'bob' said:\nThe sky is crimson."},
    ]


def get_text_compressors() -> List[TextCompressor]:
    compressors: List[TextCompressor] = [_MockTextCompressor()]
    try:
        from autogen.agentchat.contrib.capabilities.text_compressors import LLMLingua

        compressors.append(LLMLingua())
    except ImportError:
        pass

    return compressors


@pytest.fixture
def message_history_limiter() -> MessageHistoryLimiter:
    return MessageHistoryLimiter(max_messages=3)


@pytest.fixture
def message_history_limiter_keep_first() -> MessageHistoryLimiter:
    return MessageHistoryLimiter(max_messages=3, keep_first_message=True)


@pytest.fixture
def message_token_limiter() -> MessageTokenLimiter:
    return MessageTokenLimiter(max_tokens_per_message=3)


@pytest.fixture
def message_token_limiter_with_threshold() -> MessageTokenLimiter:
    return MessageTokenLimiter(max_tokens_per_message=1, min_tokens=10)


def _filter_dict_test(
    post_transformed_message: Dict, pre_transformed_messages: Dict, roles: List[str], exclude_filter: bool
) -> bool:
    is_role = post_transformed_message["role"] in roles
    if exclude_filter:
        is_role = not is_role

    if isinstance(post_transformed_message["content"], list):
        condition = (
            len(post_transformed_message["content"][0]["text"]) < len(pre_transformed_messages["content"][0]["text"])
            if is_role
            else len(post_transformed_message["content"][0]["text"])
            == len(pre_transformed_messages["content"][0]["text"])
        )
    else:
        condition = (
            len(post_transformed_message["content"]) < len(pre_transformed_messages["content"])
            if is_role
            else len(post_transformed_message["content"]) == len(pre_transformed_messages["content"])
        )

    return condition


# MessageHistoryLimiter


@pytest.mark.parametrize(
    "messages, expected_messages_len",
    [
        (get_long_messages(), 3),
        (get_short_messages(), 3),
        (get_no_content_messages(), 2),
        (get_tool_messages(), 2),
        (get_tool_messages_kept(), 2),
    ],
)
def test_message_history_limiter_apply_transform(message_history_limiter, messages, expected_messages_len):
    transformed_messages = message_history_limiter.apply_transform(messages)
    assert len(transformed_messages) == expected_messages_len

    if messages == get_tool_messages_kept():
        assert transformed_messages[0]["role"] == "tool_calls"
        assert transformed_messages[1]["role"] == "tool"


@pytest.mark.parametrize(
    "messages, expected_messages_len",
    [
        (get_long_messages(), 3),
        (get_short_messages(), 3),
        (get_no_content_messages(), 2),
        (get_tool_messages(), 3),
        (get_tool_messages_kept(), 3),
    ],
)
def test_message_history_limiter_apply_transform_keep_first(
    message_history_limiter_keep_first, messages, expected_messages_len
):
    transformed_messages = message_history_limiter_keep_first.apply_transform(messages)
    assert len(transformed_messages) == expected_messages_len

    if messages == get_tool_messages_kept():
        assert transformed_messages[1]["role"] == "tool_calls"
        assert transformed_messages[2]["role"] == "tool"


@pytest.mark.parametrize(
    "messages, expected_logs, expected_effect",
    [
        (get_long_messages(), "Removed 2 messages. Number of messages reduced from 5 to 3.", True),
        (get_short_messages(), "No messages were removed.", False),
        (get_no_content_messages(), "No messages were removed.", False),
        (get_tool_messages(), "Removed 3 messages. Number of messages reduced from 5 to 2.", True),
        (get_tool_messages_kept(), "Removed 3 messages. Number of messages reduced from 5 to 2.", True),
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
    transformed_messages = message_token_limiter.apply_transform(copy.deepcopy(messages))
    assert (
        sum(count_text_tokens(msg["content"]) for msg in transformed_messages if "content" in msg)
        == expected_token_count
    )
    assert len(transformed_messages) == expected_messages_len


@pytest.mark.parametrize("messages", [get_long_messages(), get_short_messages()])
def test_message_token_limiter_with_filter(messages):
    # Test truncating all messages except for user
    message_token_limiter = MessageTokenLimiter(max_tokens_per_message=0, filter_dict={"role": "user"})
    transformed_messages = message_token_limiter.apply_transform(copy.deepcopy(messages))

    pre_post_messages = zip(messages, transformed_messages)

    for pre_transform, post_transform in pre_post_messages:
        assert _filter_dict_test(post_transform, pre_transform, ["user"], exclude_filter=True)

    # Test truncating all user messages only
    message_token_limiter = MessageTokenLimiter(
        max_tokens_per_message=0, filter_dict={"role": "user"}, exclude_filter=False
    )
    transformed_messages = message_token_limiter.apply_transform(copy.deepcopy(messages))

    pre_post_messages = zip(messages, transformed_messages)
    for pre_transform, post_transform in pre_post_messages:
        assert _filter_dict_test(post_transform, pre_transform, ["user"], exclude_filter=False)


@pytest.mark.parametrize(
    "messages, expected_token_count, expected_messages_len",
    [(get_long_messages(), 5, 5), (get_short_messages(), 5, 3), (get_no_content_messages(), 0, 2)],
)
def test_message_token_limiter_with_threshold_apply_transform(
    message_token_limiter_with_threshold, messages, expected_token_count, expected_messages_len
):
    transformed_messages = message_token_limiter_with_threshold.apply_transform(messages)
    assert (
        sum(count_text_tokens(msg["content"]) for msg in transformed_messages if "content" in msg)
        == expected_token_count
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


# TextMessageCompressor tests


@pytest.mark.parametrize("text_compressor", get_text_compressors())
def test_text_compression(text_compressor):
    """Test the TextMessageCompressor transform."""

    compressor = TextMessageCompressor(text_compressor=text_compressor)

    text = "Run this test with a long string. "
    messages = [
        {"role": "assistant", "content": [{"type": "text", "text": "".join([text] * 3)}]},
        {"role": "role", "content": [{"type": "text", "text": "".join([text] * 3)}]},
        {"role": "assistant", "content": [{"type": "text", "text": "".join([text] * 3)}]},
        {"role": "assistant", "content": [{"type": "text", "text": "".join([text] * 3)}]},
    ]

    transformed_messages = compressor.apply_transform([{"content": text}])

    assert len(transformed_messages[0]["content"]) < len(text)

    # Test compressing all messages
    compressor = TextMessageCompressor(text_compressor=text_compressor)
    transformed_messages = compressor.apply_transform(copy.deepcopy(messages))

    pre_post_messages = zip(messages, transformed_messages)
    for pre_transform, post_transform in pre_post_messages:
        assert len(post_transform["content"][0]["text"]) < len(pre_transform["content"][0]["text"])


@pytest.mark.parametrize("messages", [get_long_messages(), get_short_messages()])
@pytest.mark.parametrize("text_compressor", get_text_compressors())
def test_text_compression_with_filter(messages, text_compressor):
    # Test truncating all messages except for user
    compressor = TextMessageCompressor(text_compressor=text_compressor, filter_dict={"role": "user"})
    transformed_messages = compressor.apply_transform(copy.deepcopy(messages))

    pre_post_messages = zip(messages, transformed_messages)
    for pre_transform, post_transform in pre_post_messages:
        assert _filter_dict_test(post_transform, pre_transform, ["user"], exclude_filter=True)

    # Test truncating all user messages only
    compressor = TextMessageCompressor(
        text_compressor=text_compressor, filter_dict={"role": "user"}, exclude_filter=False
    )
    transformed_messages = compressor.apply_transform(copy.deepcopy(messages))

    pre_post_messages = zip(messages, transformed_messages)
    for pre_transform, post_transform in pre_post_messages:
        assert _filter_dict_test(post_transform, pre_transform, ["user"], exclude_filter=False)


@pytest.mark.parametrize("messages", [get_messages_with_names()])
def test_message_content_name(messages):
    # Test including content name in messages

    # Add name at the start with format: "'{name}' said:\n"
    content_transform = TextMessageContentName(position="start", format_string="'{name}' said:\n")
    transformed_messages = content_transform.apply_transform(messages=messages)

    assert transformed_messages == get_messages_with_names_post_start()

    # Add name at the end with format: "\n(said '{name}')"
    content_transform = TextMessageContentName(position="end", format_string="\n(said '{name}')")
    transformed_messages_end = content_transform.apply_transform(messages=messages)

    assert transformed_messages_end == get_messages_with_names_post_end()

    # Test filtering out exclusion
    content_transform = TextMessageContentName(
        position="start",
        format_string="'{name}' said:\n",
        filter_dict={"name": ["charlie"]},
        exclude_filter=True,  # Exclude
    )

    transformed_messages_end = content_transform.apply_transform(messages=messages)

    assert transformed_messages_end == get_messages_with_names_post_filtered()

    # Test filtering (inclusion)
    content_transform = TextMessageContentName(
        position="start",
        format_string="'{name}' said:\n",
        filter_dict={"name": ["mary", "bob"]},
        exclude_filter=False,  # Include
    )

    transformed_messages_end = content_transform.apply_transform(messages=messages)

    assert transformed_messages_end == get_messages_with_names_post_filtered()

    # Test instantiation
    with pytest.raises(AssertionError):
        TextMessageContentName(position=123)  # Invalid type for position

    with pytest.raises(AssertionError):
        TextMessageContentName(position="middle")  # Invalid value for position

    with pytest.raises(AssertionError):
        TextMessageContentName(format_string=123)  # Invalid type for format_string

    with pytest.raises(AssertionError):
        TextMessageContentName(format_string="Agent:\n")  # Missing '{name}' in format_string

    with pytest.raises(AssertionError):
        TextMessageContentName(deduplicate="yes")  # Invalid type for deduplicate


if __name__ == "__main__":
    long_messages = get_long_messages()
    short_messages = get_short_messages()
    no_content_messages = get_no_content_messages()
    tool_messages = get_tool_messages()
    msg_history_limiter = MessageHistoryLimiter(max_messages=3)
    msg_history_limiter_keep_first = MessageHistoryLimiter(max_messages=3, keep_first=True)
    msg_token_limiter = MessageTokenLimiter(max_tokens_per_message=3)
    msg_token_limiter_with_threshold = MessageTokenLimiter(max_tokens_per_message=1, min_tokens=10)

    # Test Parameters
    message_history_limiter_apply_transform_parameters = {
        "messages": [long_messages, short_messages, no_content_messages, tool_messages],
        "expected_messages_len": [3, 3, 2, 4],
    }

    message_history_limiter_get_logs_parameters = {
        "messages": [long_messages, short_messages, no_content_messages, tool_messages],
        "expected_logs": [
            "Removed 2 messages. Number of messages reduced from 5 to 3.",
            "No messages were removed.",
            "No messages were removed.",
            "Removed 1 messages. Number of messages reduced from 5 to 4.",
        ],
        "expected_effect": [True, False, False, True],
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

    for messages, expected_messages_len in zip(
        message_history_limiter_apply_transform_parameters["messages"],
        message_history_limiter_apply_transform_parameters["expected_messages_len"],
    ):
        test_message_history_limiter_apply_transform_keep_first(
            msg_history_limiter_keep_first, messages, expected_messages_len
        )

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
