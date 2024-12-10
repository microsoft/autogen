import asyncio
import json
import logging
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff, TaskResult
from autogen_agentchat.messages import (
    HandoffMessage,
    MultiModalMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from autogen_core import Image
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage
from utils import FileLogHandler

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
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    result = await agent.run(task="task")

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
    assert result.messages[3].content == "pass"
    assert result.messages[3].models_usage is None

    # Test streaming.
    mock._curr_index = 0  # pyright: ignore
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_run_with_tools_and_reflection(monkeypatch: pytest.MonkeyPatch) -> None:
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
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
        reflect_on_tool_use=True,
    )
    result = await agent.run(task="task")

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
    assert result.messages[3].content == "Hello"
    assert result.messages[3].models_usage is not None
    assert result.messages[3].models_usage.completion_tokens == 5
    assert result.messages[3].models_usage.prompt_tokens == 10

    # Test streaming.
    mock._curr_index = 0  # pyright: ignore
    index = 0
    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test state saving and loading.
    state = await agent.save_state()
    agent2 = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    await agent2.load_state(state)
    state2 = await agent2.save_state()
    assert state == state2


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


@pytest.mark.asyncio
async def test_multi_modal_task(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
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
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    agent = AssistantAgent(name="assistant", model_client=OpenAIChatCompletionClient(model=model, api_key=""))
    # Generate a random base64 image.
    img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
    result = await agent.run(task=MultiModalMessage(source="user", content=["Test", Image.from_base64(img_base64)]))
    assert len(result.messages) == 2


@pytest.mark.asyncio
async def test_invalid_model_capabilities() -> None:
    model = "random-model"
    model_client = OpenAIChatCompletionClient(
        model=model, api_key="", model_capabilities={"vision": False, "function_calling": False, "json_output": False}
    )

    with pytest.raises(ValueError):
        agent = AssistantAgent(
            name="assistant",
            model_client=model_client,
            tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
        )

    with pytest.raises(ValueError):
        agent = AssistantAgent(name="assistant", model_client=model_client, handoffs=["agent2"])

    with pytest.raises(ValueError):
        agent = AssistantAgent(name="assistant", model_client=model_client)
        # Generate a random base64 image.
        img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
        await agent.run(task=MultiModalMessage(source="user", content=["Test", Image.from_base64(img_base64)]))
