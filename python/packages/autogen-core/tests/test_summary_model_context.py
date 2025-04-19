import functools
from typing import Any, Generator, List, cast
from unittest.mock import AsyncMock, Mock

import pytest
from autogen_core.code_executor import ImportFromModule
from autogen_core.model_context import SummarizedChatCompletionContext
from autogen_core.model_context.conditions import ExternalMessageCompletion, SummaryFunction
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


## test summary function
def test_summary_function_init() -> None:
    def sample_func(messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> List[LLMMessage]:
        return messages

    # Test with basic function
    sf = SummaryFunction(sample_func)
    assert sf.name == "sample_func"

    # Test with custom name
    sf = SummaryFunction(sample_func, name="custom_name")
    assert sf.name == "custom_name"

    # Test with partial function
    partial_func = functools.partial(sample_func)
    sf = SummaryFunction(partial_func)
    assert sf.name == "sample_func"


def test_summary_function_run() -> None:
    mock_messages = cast(List[LLMMessage], [Mock(spec=LLMMessage)])
    mock_non_summary = cast(List[LLMMessage], [Mock(spec=LLMMessage)])

    def sample_func(messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> List[LLMMessage]:
        return messages

    sf = SummaryFunction(sample_func)
    result = sf.run(mock_messages, mock_non_summary)
    assert result == mock_messages


def test_summary_function_dump_and_load() -> None:
    def sample_func(messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> List[LLMMessage]:
        return messages

    import_list = ImportFromModule("typing", ["List"])
    import_llmmessage = ImportFromModule("autogen_core.models", ["LLMMessage"])

    sf = SummaryFunction(sample_func, global_imports=[import_list, import_llmmessage])
    config = sf.dump_component()

    assert config.config["name"] == "sample_func"
    assert (
        config.config["source_code"]
        == "def sample_func(messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> List[LLMMessage]:\n    return messages\n"
    )

    loaded_sf = SummaryFunction.load_component(config)
    assert loaded_sf.name == "sample_func"
    assert loaded_sf._func.__code__.co_code == sf._func.__code__.co_code  # pyright: ignore[reportPrivateUsage]
    assert loaded_sf._signature == sf._signature  # pyright: ignore[reportPrivateUsage]
