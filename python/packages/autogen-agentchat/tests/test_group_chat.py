import asyncio
import json
import logging
import tempfile
from typing import Any, AsyncGenerator, List, Sequence

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    AssistantAgent,
    BaseChatAgent,
    CodeExecutorAgent,
)
from autogen_agentchat.base import Handoff, Response, TaskResult
from autogen_agentchat.conditions import HandoffTermination, MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (
    AgentMessage,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from autogen_agentchat.teams import (
    RoundRobinGroupChat,
    SelectorGroupChat,
    Swarm,
)
from autogen_agentchat.teams._group_chat._round_robin_group_chat import RoundRobinGroupChatManager
from autogen_agentchat.teams._group_chat._selector_group_chat import SelectorGroupChatManager
from autogen_agentchat.teams._group_chat._swarm_group_chat import SwarmGroupChatManager
from autogen_agentchat.ui import Console
from autogen_core import AgentId, CancellationToken, FunctionCall
from autogen_core.components.code_executor import LocalCommandLineCodeExecutor
from autogen_core.components.models import FunctionExecutionResult
from autogen_core.components.tools import FunctionTool
from autogen_ext.models import OpenAIChatCompletionClient, ReplayChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage
from utils import FileLogHandler

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

    def reset(self) -> None:
        self._curr_index = 0


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        if len(messages) > 0:
            assert isinstance(messages[0], TextMessage)
            self._last_message = messages[0].content
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=messages[0].content, source=self.name))
        else:
            assert self._last_message is not None
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=self._last_message, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_message = None


class _StopAgent(_EchoAgent):
    def __init__(self, name: str, description: str, *, stop_at: int = 1) -> None:
        super().__init__(name, description)
        self._count = 0
        self._stop_at = stop_at

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage, StopMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        self._count += 1
        if self._count < self._stop_at:
            return await super().on_messages(messages, cancellation_token)
        return Response(chat_message=StopMessage(content="TERMINATE", source=self.name))


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
        coding_assistant_agent = AssistantAgent(
            "coding_assistant", model_client=OpenAIChatCompletionClient(model=model, api_key="")
        )
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat(
            participants=[coding_assistant_agent, code_executor_agent], termination_condition=termination
        )
        result = await team.run(
            task="Write a program that prints 'Hello, world!'",
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

        assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

        # Test streaming.
        mock.reset()
        index = 0
        await team.reset()
        async for message in team.run_stream(
            task="Write a program that prints 'Hello, world!'",
        ):
            if isinstance(message, TaskResult):
                assert message == result
            else:
                assert message == result.messages[index]
            index += 1

        # Test message input.
        # Text message.
        mock.reset()
        index = 0
        await team.reset()
        result_2 = await team.run(
            task=TextMessage(content="Write a program that prints 'Hello, world!'", source="user")
        )
        assert result == result_2

        # Test multi-modal message.
        mock.reset()
        index = 0
        await team.reset()
        result_2 = await team.run(
            task=MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")
        )
        assert result.messages[0].content == result_2.messages[0].content[0]
        assert result.messages[1:] == result_2.messages[1:]


@pytest.mark.asyncio
async def test_round_robin_group_chat_state() -> None:
    model_client = ReplayChatCompletionClient(
        ["No facts", "No plan", "print('Hello, world!')", "TERMINATE"],
    )
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = RoundRobinGroupChat(participants=[agent1, agent2], termination_condition=termination)
    await team1.run(task="Write a program that prints 'Hello, world!'")
    state = await team1.save_state()

    agent3 = AssistantAgent("agent1", model_client=model_client)
    agent4 = AssistantAgent("agent2", model_client=model_client)
    team2 = RoundRobinGroupChat(participants=[agent3, agent4], termination_condition=termination)
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2
    assert agent3._model_context == agent1._model_context  # pyright: ignore
    assert agent4._model_context == agent2._model_context  # pyright: ignore
    manager_1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team1._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team2._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._current_turn == manager_2._current_turn  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore


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
    tool_use_agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        tools=[tool],
    )
    echo_agent = _EchoAgent("echo_agent", description="echo agent")
    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat(participants=[tool_use_agent, echo_agent], termination_condition=termination)
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )

    assert len(result.messages) == 6
    assert isinstance(result.messages[0], TextMessage)  # task
    assert isinstance(result.messages[1], ToolCallMessage)  # tool call
    assert isinstance(result.messages[2], ToolCallResultMessage)  # tool call result
    assert isinstance(result.messages[3], TextMessage)  # tool use agent response
    assert isinstance(result.messages[4], TextMessage)  # echo agent response
    assert isinstance(result.messages[5], TextMessage)  # tool use agent response
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

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

    # Test streaming.
    tool_use_agent._model_context.clear()  # pyright: ignore
    mock.reset()
    index = 0
    await team.reset()
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console.
    tool_use_agent._model_context.clear()  # pyright: ignore
    mock.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_resume_and_reset() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    termination = MaxMessageTermination(3)
    team = RoundRobinGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], termination_condition=termination)
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 3
    assert result.messages[1].source == "agent_1"
    assert result.messages[2].source == "agent_2"
    assert result.stop_reason is not None

    # Resume.
    result = await team.run()
    assert len(result.messages) == 3
    assert result.messages[0].source == "agent_3"
    assert result.messages[1].source == "agent_4"
    assert result.messages[2].source == "agent_1"
    assert result.stop_reason is not None

    # Reset.
    await team.reset()
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 3
    assert result.messages[1].source == "agent_1"
    assert result.messages[2].source == "agent_2"
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_round_robin_group_chat_max_turn() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    team = RoundRobinGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], max_turns=3)
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 4
    assert result.messages[1].source == "agent_1"
    assert result.messages[2].source == "agent_2"
    assert result.messages[3].source == "agent_3"
    assert result.stop_reason is not None

    # Resume.
    result = await team.run()
    assert len(result.messages) == 3
    assert result.messages[0].source == "agent_4"
    assert result.messages[1].source == "agent_1"
    assert result.messages[2].source == "agent_2"
    assert result.stop_reason is not None

    # Reset.
    await team.reset()
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 4
    assert result.messages[1].source == "agent_1"
    assert result.messages[2].source == "agent_2"
    assert result.messages[3].source == "agent_3"
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_round_robin_group_chat_cancellation() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    # Set max_turns to a large number to avoid stopping due to max_turns before cancellation.
    team = RoundRobinGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], max_turns=1000)
    cancellation_token = CancellationToken()
    run_task = asyncio.create_task(
        team.run(
            task="Write a program that prints 'Hello, world!'",
            cancellation_token=cancellation_token,
        )
    )
    await asyncio.sleep(0.1)
    # Cancel the task.
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task

    # Total messages produced so far.
    total_messages = agent_1.total_messages + agent_2.total_messages + agent_3.total_messages + agent_4.total_messages

    # Still can run again and finish the task.
    result = await team.run()
    assert len(result.messages) + total_messages == 1000


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
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        termination_condition=termination,
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 6
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent3"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.messages[4].source == "agent2"
    assert result.messages[5].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    mock.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console.
    mock.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


@pytest.mark.asyncio
async def test_selector_group_chat_state() -> None:
    model_client = ReplayChatCompletionClient(
        ["agent1", "No facts", "agent2", "No plan", "agent1", "print('Hello, world!')", "agent2", "TERMINATE"],
    )
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = SelectorGroupChat(
        participants=[agent1, agent2], termination_condition=termination, model_client=model_client
    )
    await team1.run(task="Write a program that prints 'Hello, world!'")
    state = await team1.save_state()

    agent3 = AssistantAgent("agent1", model_client=model_client)
    agent4 = AssistantAgent("agent2", model_client=model_client)
    team2 = SelectorGroupChat(
        participants=[agent3, agent4], termination_condition=termination, model_client=model_client
    )
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2
    assert agent3._model_context == agent1._model_context  # pyright: ignore
    assert agent4._model_context == agent2._model_context  # pyright: ignore
    manager_1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team1._team_id),  # pyright: ignore
        SelectorGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team2._team_id),  # pyright: ignore
        SelectorGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._previous_speaker == manager_2._previous_speaker  # pyright: ignore


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
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 5
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent1"
    assert result.messages[3].source == "agent2"
    assert result.messages[4].source == "agent1"
    # only one chat completion was called
    assert mock._curr_index == 1  # pyright: ignore
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    mock.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    async for message in team.run_stream(task="Write a program that prints 'Hello, world!'"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console.
    mock.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


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
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        termination_condition=termination,
        allow_repeated_speaker=True,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 4
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    mock.reset()
    index = 0
    await team.reset()
    async for message in team.run_stream(task="Write a program that prints 'Hello, world!'"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console.
    mock.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


@pytest.mark.asyncio
async def test_selector_group_chat_custom_selector(monkeypatch: pytest.MonkeyPatch) -> None:
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
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    agent1 = _EchoAgent("agent1", description="echo agent 1")
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    agent4 = _EchoAgent("agent4", description="echo agent 4")

    def _select_agent(messages: Sequence[AgentMessage]) -> str | None:
        if len(messages) == 0:
            return "agent1"
        elif messages[-1].source == "agent1":
            return "agent2"
        elif messages[-1].source == "agent2":
            return None
        elif messages[-1].source == "agent3":
            return "agent4"
        else:
            return "agent1"

    termination = MaxMessageTermination(6)
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3, agent4],
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        selector_func=_select_agent,
        termination_condition=termination,
    )
    result = await team.run(task="task")
    assert len(result.messages) == 6
    assert result.messages[1].source == "agent1"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent3"
    assert result.messages[4].source == "agent4"
    assert result.messages[5].source == "agent1"
    assert (
        result.stop_reason is not None
        and result.stop_reason == "Maximum number of messages 6 reached, current message count: 6"
    )


class _HandOffAgent(BaseChatAgent):
    def __init__(self, name: str, description: str, next_agent: str) -> None:
        super().__init__(name, description)
        self._next_agent = next_agent

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [HandoffMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(
            chat_message=HandoffMessage(
                content=f"Transferred to {self._next_agent}.", target=self._next_agent, source=self.name
            )
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


@pytest.mark.asyncio
async def test_swarm_handoff() -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    termination = MaxMessageTermination(6)
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination)
    result = await team.run(task="task")
    assert len(result.messages) == 6
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."
    assert result.messages[2].content == "Transferred to first_agent."
    assert result.messages[3].content == "Transferred to second_agent."
    assert result.messages[4].content == "Transferred to third_agent."
    assert result.messages[5].content == "Transferred to first_agent."
    assert (
        result.stop_reason is not None
        and result.stop_reason == "Maximum number of messages 6 reached, current message count: 6"
    )

    # Test streaming.
    index = 0
    await team.reset()
    stream = team.run_stream(task="task")
    async for message in stream:
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test save and load.
    state = await team.save_state()
    first_agent2 = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent2 = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent2 = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")
    team2 = Swarm([second_agent2, first_agent2, third_agent2], termination_condition=termination)
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2
    manager_1 = await team._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId("group_chat_manager", team2._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._current_speaker == manager_2._current_speaker  # pyright: ignore


@pytest.mark.asyncio
async def test_swarm_handoff_using_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
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
                                    name="handoff_to_agent2",
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

    agent1 = AssistantAgent(
        "agent1",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        handoffs=[Handoff(target="agent2", name="handoff_to_agent2", message="handoff to agent2")],
    )
    agent2 = _HandOffAgent("agent2", description="agent 2", next_agent="agent1")
    termination = TextMentionTermination("TERMINATE")
    team = Swarm([agent1, agent2], termination_condition=termination)
    result = await team.run(task="task")
    assert len(result.messages) == 7
    assert result.messages[0].content == "task"
    assert isinstance(result.messages[1], ToolCallMessage)
    assert isinstance(result.messages[2], ToolCallResultMessage)
    assert result.messages[3].content == "handoff to agent2"
    assert result.messages[4].content == "Transferred to agent1."
    assert result.messages[5].content == "Hello"
    assert result.messages[6].content == "TERMINATE"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    agent1._model_context.clear()  # pyright: ignore
    mock.reset()
    index = 0
    await team.reset()
    stream = team.run_stream(task="task")
    async for message in stream:
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console
    agent1._model_context.clear()  # pyright: ignore
    mock.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="task"))
    assert result2 == result


@pytest.mark.asyncio
async def test_swarm_pause_and_resume() -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    team = Swarm([second_agent, first_agent, third_agent], max_turns=1)
    result = await team.run(task="task")
    assert len(result.messages) == 2
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."

    # Resume with a new task.
    result = await team.run(task="new task")
    assert len(result.messages) == 2
    assert result.messages[0].content == "new task"
    assert result.messages[1].content == "Transferred to first_agent."

    # Resume with the same task.
    result = await team.run()
    assert len(result.messages) == 1
    assert result.messages[0].content == "Transferred to second_agent."


@pytest.mark.asyncio
async def test_swarm_with_handoff_termination() -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    # Handoff to an existing agent.
    termination = HandoffTermination(target="third_agent")
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination)
    # Start
    result = await team.run(task="task")
    assert len(result.messages) == 2
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."
    # Resume existing.
    result = await team.run()
    assert len(result.messages) == 3
    assert result.messages[0].content == "Transferred to first_agent."
    assert result.messages[1].content == "Transferred to second_agent."
    assert result.messages[2].content == "Transferred to third_agent."
    # Resume new task.
    result = await team.run(task="new task")
    assert len(result.messages) == 4
    assert result.messages[0].content == "new task"
    assert result.messages[1].content == "Transferred to first_agent."
    assert result.messages[2].content == "Transferred to second_agent."
    assert result.messages[3].content == "Transferred to third_agent."

    # Handoff to a non-existing agent.
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="non_existing_agent")
    termination = HandoffTermination(target="non_existing_agent")
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination)
    # Start
    result = await team.run(task="task")
    assert len(result.messages) == 3
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."
    assert result.messages[2].content == "Transferred to non_existing_agent."
    # Attempt to resume.
    with pytest.raises(ValueError):
        await team.run()
    # Attempt to resume with a new task.
    with pytest.raises(ValueError):
        await team.run(task="new task")
    # Resume with a HandoffMessage
    result = await team.run(task=HandoffMessage(content="Handoff to first_agent.", target="first_agent", source="user"))
    assert len(result.messages) == 4
    assert result.messages[0].content == "Handoff to first_agent."
    assert result.messages[1].content == "Transferred to second_agent."
    assert result.messages[2].content == "Transferred to third_agent."
    assert result.messages[3].content == "Transferred to non_existing_agent."
