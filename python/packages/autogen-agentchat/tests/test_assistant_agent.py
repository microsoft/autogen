import asyncio
import json
import logging
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent, Handoff
from autogen_agentchat.base import TaskResult
from autogen_agentchat.logging import FileLogHandler
from autogen_agentchat.messages import HandoffMessage, TextMessage, ToolCallMessage, ToolCallResultMessage
from autogen_core.components.tools import FunctionTool
from autogen_ext.models import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_assistant_agent.log"))


class _MockChatCompletion:
    def __init__(self, chat_completions: List[ChatCompletion]) -> None:
        self._saved_chat_completions = chat_completions
        self._curr_index = 0

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self._curr_index]
        self._curr_index += 1
        return completion


def _pass_function(input: str) -> str:
    return "pass"


async def _fail_function(input: str) -> str:
    return "fail"


async def _echo_function(input: str) -> str:
    return input


@pytest.mark.asyncio
async def test_run_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(
                    finish_reason="stop", index=0, message=ChatCompletionMessage(content="TERMINATE", role="assistant")
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallMessage)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 5
    assert result.messages[1].models_usage.prompt_tokens == 10
    assert isinstance(result.messages[2], ToolCallResultMessage)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], TextMessage)
    assert result.messages[3].models_usage is not None
    assert result.messages[3].models_usage.completion_tokens == 5
    assert result.messages[3].models_usage.prompt_tokens == 10

    # Test streaming.
    mock._curr_index = 0  # pyright: ignore
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1


@pytest.mark.asyncio
async def test_handoffs(monkeypatch: pytest.MonkeyPatch) -> None:
    handoff = Handoff(target="agent2")
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name=handoff.name,
                                    arguments=json.dumps({}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=42, completion_tokens=43, total_tokens=85),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
        handoffs=[handoff],
    )
    assert HandoffMessage in tool_use_agent.produced_message_types
    result = await tool_use_agent.run(task="task")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    assert isinstance(result.messages[1], ToolCallMessage)
    assert result.messages[1].models_usage is not None
    assert result.messages[1].models_usage.completion_tokens == 43
    assert result.messages[1].models_usage.prompt_tokens == 42
    assert isinstance(result.messages[2], ToolCallResultMessage)
    assert result.messages[2].models_usage is None
    assert isinstance(result.messages[3], HandoffMessage)
    assert result.messages[3].content == handoff.message
    assert result.messages[3].target == handoff.target
    assert result.messages[3].models_usage is None

    # Test streaming.
    mock._curr_index = 0  # pyright: ignore
    index = 0
    async for message in tool_use_agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1
