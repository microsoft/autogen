import asyncio
from typing import Any, Generator

import pytest
from autogen_core.model_context.conditions import (
    ExternalMessageCompletion,
    FunctionCallMessageCompletion,
    MaxMessageCompletion,
    MessageCompletionException,
    SourceMatchMessageCompletion,
    StopMessageCompletion,
    TextMentionMessageCompletion,
    TextMessageMessageCompletion,
    TimeoutMessageCompletion,
    TokenUsageMessageCompletion,
    TriggerMessage,
)
from autogen_core.models import AssistantMessage, FunctionExecutionResult, FunctionExecutionResultMessage, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient


# Test StopMessageCompletion
@pytest.fixture
def stop_condition() -> Generator[Any, Any, Any]:
    condition = StopMessageCompletion()
    yield condition
    asyncio.run(condition.reset())


def test_stop_initial_state(stop_condition: Any) -> None:
    assert not stop_condition.triggered


def test_stop_trigger_on_trigger_message(stop_condition: Any) -> None:
    trigger_msg = TriggerMessage(content="Stop", source="test")
    result = asyncio.run(stop_condition([trigger_msg]))
    assert result is not None
    assert stop_condition.triggered


def test_stop_no_trigger_on_regular_message(stop_condition: Any) -> None:
    message = UserMessage(content="Regular message", source="test")
    result = asyncio.run(stop_condition([message]))
    assert result is None
    assert not stop_condition.triggered


def test_stop_exception_when_already_triggered(stop_condition: Any) -> None:
    trigger_msg = TriggerMessage(content="Stop", source="test")
    asyncio.run(stop_condition([trigger_msg]))
    with pytest.raises(MessageCompletionException):
        asyncio.run(stop_condition([trigger_msg]))


def test_stop_reset(stop_condition: Any) -> None:
    trigger_msg = TriggerMessage(content="Stop", source="test")
    asyncio.run(stop_condition([trigger_msg]))
    assert stop_condition.triggered
    asyncio.run(stop_condition.reset())
    assert not stop_condition.triggered


# Test MaxMessageCompletion
@pytest.fixture
def max_condition() -> Generator[Any, Any, Any]:
    condition = MaxMessageCompletion(max_messages=2)
    yield condition
    asyncio.run(condition.reset())


def test_max_initial_state(max_condition: Any) -> None:
    assert not max_condition.triggered


def test_max_trigger_when_max_reached(max_condition: Any) -> None:
    msg1 = UserMessage(content="Message 1", source="test")
    msg2 = AssistantMessage(content="Message 2", source="test")

    result1 = asyncio.run(max_condition([msg1]))
    assert result1 is None
    assert not max_condition.triggered

    result2 = asyncio.run(max_condition([msg2]))
    assert result2 is not None
    assert max_condition.triggered


def test_max_exception_when_already_triggered(max_condition: Any) -> None:
    msg1 = UserMessage(content="Message 1", source="test")
    msg2 = AssistantMessage(content="Message 2", source="test")

    asyncio.run(max_condition([msg1, msg2]))
    assert max_condition.triggered

    with pytest.raises(MessageCompletionException):
        asyncio.run(max_condition([msg1]))


def test_max_reset(max_condition: Any) -> None:
    msg1 = UserMessage(content="Message 1", source="test")
    msg2 = AssistantMessage(content="Message 2", source="test")

    asyncio.run(max_condition([msg1, msg2]))
    assert max_condition.triggered

    asyncio.run(max_condition.reset())
    assert not max_condition.triggered


# TextMentionMessageCompletion fixture
@pytest.fixture
def text_mention_condition() -> Generator[Any, Any, Any]:
    trigger_text = "trigger me"
    condition = TextMentionMessageCompletion(text=trigger_text)
    yield condition, trigger_text
    asyncio.run(condition.reset())


# Test TextMentionMessageCompletion
def test_text_mention_initial_state(text_mention_condition: Any) -> None:
    condition, _ = text_mention_condition
    assert not condition.triggered


def test_text_mention_trigger_when_text_found(text_mention_condition: Any) -> None:
    condition, trigger_text = text_mention_condition
    message = AssistantMessage(content=f"This message contains {trigger_text} somewhere", source="test")
    result = asyncio.run(condition([message]))
    assert result is not None
    assert condition.triggered


def test_text_mention_no_trigger_when_text_not_found(text_mention_condition: Any) -> None:
    condition, _ = text_mention_condition
    message = AssistantMessage(content="This message doesn't contain the trigger", source="test")
    result = asyncio.run(condition([message]))
    assert result is None
    assert not condition.triggered


def test_text_mention_case_sensitive(text_mention_condition: Any) -> None:
    condition, trigger_text = text_mention_condition
    upper_message = AssistantMessage(content=f"This message contains {trigger_text.upper()} somewhere", source="test")
    result = asyncio.run(condition([upper_message]))
    # Default is case insensitive
    assert result is None
    assert not condition.triggered


# Test TimeoutMessageCompletion
@pytest.fixture
def timeout_condition() -> Generator[Any, Any, Any]:
    condition = TimeoutMessageCompletion(timeout_seconds=0.2)  # Short timeout for testing
    yield condition
    asyncio.run(condition.reset())


def test_timeout_initial_state(timeout_condition: Any) -> None:
    assert not timeout_condition.triggered


def test_timeout_triggers_after_timeout(timeout_condition: Any) -> None:
    asyncio.run(asyncio.sleep(0.2))  # Sleep longer than timeout
    message = UserMessage(content="Test message", source="test")
    result = asyncio.run(timeout_condition([message]))
    assert result is not None
    assert timeout_condition.triggered


def test_timeout_reset(timeout_condition: Any) -> None:
    asyncio.run(asyncio.sleep(0.2))
    message = UserMessage(content="Test message", source="test")
    asyncio.run(timeout_condition([message]))
    assert timeout_condition.triggered

    asyncio.run(timeout_condition.reset())
    assert not timeout_condition.triggered


# Test TokenUsageMessageCompletion
@pytest.fixture
def token_usage_condition() -> Generator[Any, Any, Any]:
    condition = TokenUsageMessageCompletion(
        model_client=OpenAIChatCompletionClient(model="gpt-4o"),
        token_limit=50,
    )
    yield condition
    asyncio.run(condition.reset())


def test_token_usage_initial_state(token_usage_condition: Any) -> None:
    assert not token_usage_condition.triggered


def test_token_usage_trigger_when_max_tokens_exceeded(token_usage_condition: Any) -> None:
    message = AssistantMessage(
        content="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25",  # Over than 50 tokens
        source="test",
    )
    result = asyncio.run(token_usage_condition([message]))
    assert result is not None
    assert token_usage_condition.triggered


def test_token_usage_no_trigger_when_under_max_tokens(token_usage_condition: Any) -> None:
    message = AssistantMessage(
        content="This is a test message",
        source="test",
    )
    result = asyncio.run(token_usage_condition([message]))
    assert result is None
    assert not token_usage_condition.triggered


# Test TextMessageMessageCompletion
@pytest.fixture
def text_message_condition() -> Generator[Any, Any, Any]:
    condition = TextMessageMessageCompletion(source="test_source")
    yield condition
    asyncio.run(condition.reset())


def test_text_message_initial_state(text_message_condition: Any) -> None:
    assert not text_message_condition.triggered


def test_text_message_trigger_when_source_matches(text_message_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    result = asyncio.run(text_message_condition([message]))
    assert result is not None
    assert text_message_condition.triggered


def test_text_message_no_trigger_when_source_doesnt_match(text_message_condition: Any) -> None:
    message = UserMessage(content="Test message", source="different_source")
    result = asyncio.run(text_message_condition([message]))
    assert result is None
    assert not text_message_condition.triggered


def test_text_message_exception_when_already_triggered(text_message_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    asyncio.run(text_message_condition([message]))
    with pytest.raises(MessageCompletionException):
        asyncio.run(text_message_condition([message]))


def test_text_message_reset(text_message_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    asyncio.run(text_message_condition([message]))
    assert text_message_condition.triggered
    asyncio.run(text_message_condition.reset())
    assert not text_message_condition.triggered


def test_text_message_any_source() -> None:
    condition = TextMessageMessageCompletion()  # No source specified, should match any
    message = UserMessage(content="Test message", source="any_source")
    result = asyncio.run(condition([message]))
    assert result is not None
    assert condition.triggered
    asyncio.run(condition.reset())


# Test FunctionCallMessageCompletion
@pytest.fixture
def function_call_condition() -> Generator[Any, Any, Any]:
    condition = FunctionCallMessageCompletion(function_name="test_function")
    yield condition
    asyncio.run(condition.reset())


def test_function_call_initial_state(function_call_condition: Any) -> None:
    assert not function_call_condition.triggered


def test_function_call_trigger_when_function_executed(function_call_condition: Any) -> None:
    function_content = FunctionExecutionResult(
        name="test_function",
        content="{}",
        call_id="123",
        is_error=False,
    )
    message = FunctionExecutionResultMessage(content=[function_content])
    result = asyncio.run(function_call_condition([message]))
    assert result is not None
    assert function_call_condition.triggered


def test_function_call_no_trigger_for_different_function(function_call_condition: Any) -> None:
    function_content = FunctionExecutionResult(
        name="other_function",
        content="{}",
        call_id="123",
        is_error=False,
    )
    message = FunctionExecutionResultMessage(content=[function_content])
    result = asyncio.run(function_call_condition([message]))
    assert result is None
    assert not function_call_condition.triggered


def test_function_call_exception_when_already_triggered(function_call_condition: Any) -> None:
    function_content = FunctionExecutionResult(
        name="test_function",
        content="{}",
        call_id="123",
        is_error=False,
    )
    message = FunctionExecutionResultMessage(content=[function_content])
    asyncio.run(function_call_condition([message]))
    with pytest.raises(MessageCompletionException):
        asyncio.run(function_call_condition([message]))


def test_function_call_reset(function_call_condition: Any) -> None:
    function_content = FunctionExecutionResult(
        name="test_function",
        content="{}",
        call_id="123",
        is_error=False,
    )
    message = FunctionExecutionResultMessage(content=[function_content])
    asyncio.run(function_call_condition([message]))
    assert function_call_condition.triggered
    asyncio.run(function_call_condition.reset())
    assert not function_call_condition.triggered


# Test SourceMatchMessageCompletion
@pytest.fixture
def source_match_condition() -> Generator[Any, Any, Any]:
    condition = SourceMatchMessageCompletion(sources=["test_source", "another_source"])
    yield condition
    asyncio.run(condition.reset())


def test_source_match_initial_state(source_match_condition: Any) -> None:
    assert not source_match_condition.triggered


def test_source_match_trigger_when_source_matches(source_match_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    result = asyncio.run(source_match_condition([message]))
    assert result is not None
    assert source_match_condition.triggered


def test_source_match_trigger_when_other_source_matches(source_match_condition: Any) -> None:
    message = UserMessage(content="Test message", source="another_source")
    result = asyncio.run(source_match_condition([message]))
    assert result is not None
    assert source_match_condition.triggered


def test_source_match_no_trigger_when_source_doesnt_match(source_match_condition: Any) -> None:
    message = UserMessage(content="Test message", source="non_matching_source")
    result = asyncio.run(source_match_condition([message]))
    assert result is None
    assert not source_match_condition.triggered


def test_source_match_exception_when_already_triggered(source_match_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    asyncio.run(source_match_condition([message]))
    with pytest.raises(MessageCompletionException):
        asyncio.run(source_match_condition([message]))


def test_source_match_reset(source_match_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test_source")
    asyncio.run(source_match_condition([message]))
    assert source_match_condition.triggered
    asyncio.run(source_match_condition.reset())
    assert not source_match_condition.triggered


# Test ExternalMessageCompletion
@pytest.fixture
def external_condition() -> Generator[Any, Any, Any]:
    condition = ExternalMessageCompletion()
    yield condition
    asyncio.run(condition.reset())


def test_external_initial_state(external_condition: Any) -> None:
    assert not external_condition.triggered


def test_external_no_trigger_before_set(external_condition: Any) -> None:
    message = UserMessage(content="Test message", source="test")
    result = asyncio.run(external_condition([message]))
    assert result is None
    assert not external_condition.triggered


def test_external_trigger_after_set(external_condition: Any) -> None:
    external_condition.set()
    message = UserMessage(content="Test message", source="test")
    result = asyncio.run(external_condition([message]))
    assert result is not None
    assert external_condition.triggered


def test_external_exception_when_already_triggered(external_condition: Any) -> None:
    external_condition.set()
    message = UserMessage(content="Test message", source="test")
    asyncio.run(external_condition([message]))
    with pytest.raises(MessageCompletionException):
        asyncio.run(external_condition([message]))


def test_external_reset(external_condition: Any) -> None:
    external_condition.set()
    message = UserMessage(content="Test message", source="test")
    asyncio.run(external_condition([message]))
    assert external_condition.triggered
    asyncio.run(external_condition.reset())
    assert not external_condition.triggered


# Test And and Or conditions
def test_and_condition() -> None:
    condition1 = MaxMessageCompletion(max_messages=2)
    condition2 = TextMentionMessageCompletion(text="trigger me")
    and_condition = condition1 & condition2

    message1 = UserMessage(content="Message 1", source="test")
    message2 = AssistantMessage(content="This message contains trigger me", source="test")

    result1 = asyncio.run(and_condition([message1]))
    assert result1 is None
    assert not and_condition.triggered
    asyncio.run(and_condition.reset())

    result2 = asyncio.run(and_condition([message2]))
    assert result2 is None
    assert not and_condition.triggered
    asyncio.run(and_condition.reset())

    asyncio.run(and_condition([message1, message2]))
    assert and_condition.triggered


def test_or_condition() -> None:
    condition1 = MaxMessageCompletion(max_messages=2)
    condition2 = TextMentionMessageCompletion(text="trigger me")
    or_condition = condition1 | condition2

    message1 = UserMessage(content="Message 1", source="test")
    message2 = AssistantMessage(content="This message contains trigger me", source="test")

    result1 = asyncio.run(or_condition([message1]))
    assert result1 is None
    assert not or_condition.triggered

    result2 = asyncio.run(or_condition([message2]))
    assert result2 is not None
    assert or_condition.triggered
