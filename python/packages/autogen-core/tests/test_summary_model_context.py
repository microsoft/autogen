from typing import Any, Generator, List, cast
from unittest.mock import AsyncMock

import pytest
from autogen_core.model_context import SummarizedChatCompletionContext
from autogen_core.model_context.conditions import ExternalMessageCompletion
from autogen_core.models import AssistantMessage, LLMMessage, UserMessage


def mock_summarizing_func(messages: List[LLMMessage], non_summarized_messages: List[LLMMessage]) -> List[LLMMessage]:
    return [UserMessage(source="user", content="summarized")]


@pytest.fixture
def mock_condition() -> Generator[Any, None, None]:
    mock = AsyncMock(spec=ExternalMessageCompletion)
    mock.triggered = False  # type: ignore
    mock.reset = AsyncMock()  # type: ignore
    yield mock


@pytest.mark.asyncio
async def test_initialize_with_none_initial_messages() -> None:
    context = SummarizedChatCompletionContext(
        summarizing_func=mock_summarizing_func, summarizing_condition=ExternalMessageCompletion(), initial_messages=None
    )
    messages = await context.get_messages()
    assert messages == []


@pytest.mark.asyncio
async def test_initialize_with_initial_messages() -> None:
    initial_msgs = cast(
        List[LLMMessage],
        [
            UserMessage(source="user", content="test1"),
            AssistantMessage(source="assistant", content="test2"),
        ],
    )
    context = SummarizedChatCompletionContext(
        summarizing_func=mock_summarizing_func,
        summarizing_condition=ExternalMessageCompletion(),
        initial_messages=initial_msgs,
    )
    messages = await context.get_messages()
    assert messages == initial_msgs


@pytest.mark.asyncio
async def test_add_message(mock_condition: Any) -> None:
    context = SummarizedChatCompletionContext(
        summarizing_func=mock_summarizing_func, summarizing_condition=mock_condition
    )

    message = UserMessage(source="user", content="test")
    await context.add_message(message)

    messages = await context.get_messages()
    assert message in messages
    mock_condition.assert_called_once()


@pytest.mark.asyncio
async def test_summary_called_when_condition_triggered(mock_condition: Any) -> None:
    mock_condition.triggered = True
    context = SummarizedChatCompletionContext(
        summarizing_func=mock_summarizing_func, summarizing_condition=mock_condition
    )

    await context.add_message(UserMessage(source="user", content="test"))
    messages = await context.get_messages()
    mock_condition.reset.assert_called_once()
    assert len(messages) == 1
    assert messages == [UserMessage(source="user", content="summarized")]
