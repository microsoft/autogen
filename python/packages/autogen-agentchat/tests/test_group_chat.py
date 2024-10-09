import asyncio
import json
import logging
import tempfile
from typing import Any, AsyncGenerator, List, Sequence

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    BaseChatAgent,
    ChatMessage,
    CodeExecutorAgent,
    CodingAssistantAgent,
    StopMessage,
    TextMessage,
    ToolUseAssistantAgent,
)
from autogen_agentchat.logging import FileLogHandler
from autogen_agentchat.teams import (
    RoundRobinGroupChat,
    SelectorGroupChat,
    StopMessageTermination,
)
from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.code_executor import LocalCommandLineCodeExecutor
from autogen_core.components.models import FunctionExecutionResult, OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_group_chat.log"))


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


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        if len(messages) > 0:
            assert isinstance(messages[0], TextMessage)
            self._last_message = messages[0].content
            return TextMessage(content=messages[0].content, source=self.name)
        else:
            assert self._last_message is not None
            return TextMessage(content=self._last_message, source=self.name)


class _StopAgent(_EchoAgent):
    def __init__(self, name: str, description: str, *, stop_at: int = 1) -> None:
        super().__init__(name, description)
        self._count = 0
        self._stop_at = stop_at

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        self._count += 1
        if self._count < self._stop_at:
            return await super().on_messages(messages, cancellation_token)
        return StopMessage(content="TERMINATE", source=self.name)


def _pass_function(input: str) -> str:
    return "pass"


@pytest.mark.asyncio
async def test_round_robin_group_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="""Here is the program\n ```python\nprint("Hello, world!")\n```""",
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(content="TERMINATE", role="assistant"),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = CodingAssistantAgent(
            "coding_assistant", model_client=OpenAIChatCompletionClient(model=model, api_key="")
        )
        team = RoundRobinGroupChat(participants=[coding_assistant_agent, code_executor_agent])
        result = await team.run(
            "Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination()
        )
        expected_messages = [
            "Write a program that prints 'Hello, world!'",
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "Hello, world!",
            "TERMINATE",
        ]
        # Normalize the messages to remove \r\n and any leading/trailing whitespace.
        normalized_messages = [
            msg.content.replace("\r\n", "\n").rstrip("\n") if isinstance(msg.content, str) else msg.content
            for msg in result.messages
        ]

        # Assert that all expected messages are in the collected messages
        assert normalized_messages == expected_messages


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
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
                                    name="pass",
                                    arguments=json.dumps({"input": "pass"}),
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
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
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
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    tool = FunctionTool(_pass_function, name="pass", description="pass function")
    tool_use_agent = ToolUseAssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        registered_tools=[tool],
    )
    echo_agent = _EchoAgent("echo_agent", description="echo agent")
    team = RoundRobinGroupChat(participants=[tool_use_agent, echo_agent])
    await team.run("Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination())
    context = tool_use_agent._model_context  # pyright: ignore
    assert context[0].content == "Write a program that prints 'Hello, world!'"
    assert isinstance(context[1].content, list)
    assert isinstance(context[1].content[0], FunctionCall)
    assert context[1].content[0].name == "pass"
    assert context[1].content[0].arguments == json.dumps({"input": "pass"})
    assert isinstance(context[2].content, list)
    assert isinstance(context[2].content[0], FunctionExecutionResult)
    assert context[2].content[0].content == "pass"
    assert context[2].content[0].call_id == "1"
    assert context[3].content == "Hello"


@pytest.mark.asyncio
async def test_selector_group_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent3", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent2", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent1", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent2", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent1", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)

    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=2)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )
    result = await team.run(
        "Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination()
    )
    assert len(result.messages) == 6
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent3"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.messages[4].source == "agent2"
    assert result.messages[5].source == "agent1"


@pytest.mark.asyncio
async def test_selector_group_chat_two_speakers(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent2", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)

    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=2)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )
    result = await team.run(
        "Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination()
    )
    assert len(result.messages) == 5
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent1"
    assert result.messages[3].source == "agent2"
    assert result.messages[4].source == "agent1"
    # only one chat completion was called
    assert mock._curr_index == 1  # pyright: ignore


@pytest.mark.asyncio
async def test_selector_group_chat_two_speakers_allow_repeated(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent2", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent2", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="agent1", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)

    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=1)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        allow_repeated_speaker=True,
    )
    result = await team.run(
        "Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination()
    )
    assert len(result.messages) == 4
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
