import asyncio
import json
import logging
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Mapping, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    AssistantAgent,
    BaseChatAgent,
    CodeExecutorAgent,
)
from autogen_agentchat.base import Handoff, Response, TaskResult, TerminationCondition
from autogen_agentchat.conditions import (
    HandoffTermination,
    MaxMessageTermination,
    StopMessageTermination,
    TextMentionTermination,
)
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    SelectorEvent,
    SelectSpeakerEvent,
    StopMessage,
    StructuredMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams import MagenticOneGroupChat, RoundRobinGroupChat, SelectorGroupChat, Swarm
from autogen_agentchat.teams._group_chat._round_robin_group_chat import RoundRobinGroupChatManager
from autogen_agentchat.teams._group_chat._selector_group_chat import SelectorGroupChatManager
from autogen_agentchat.teams._group_chat._swarm_group_chat import SwarmGroupChatManager
from autogen_agentchat.ui import Console
from autogen_core import AgentId, AgentRuntime, CancellationToken, FunctionCall, SingleThreadedAgentRuntime
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    UserMessage,
)
from autogen_core.tools import FunctionTool
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.replay import ReplayChatCompletionClient
from pydantic import BaseModel
from utils import FileLogHandler, compare_messages, compare_task_results

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_group_chat.log"))


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
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

    async def save_state(self) -> Mapping[str, Any]:
        return {
            "last_message": self._last_message,
            "total_messages": self._total_messages,
        }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self._last_message = state.get("last_message")
        self._total_messages = state.get("total_messages", 0)


class _FlakyAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        raise ValueError("I am a flaky agent...")

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_message = None


class _FlakyTermination(TerminationCondition):
    def __init__(self, raise_on_count: int) -> None:
        self._raise_on_count = raise_on_count
        self._count = 0

    @property
    def terminated(self) -> bool:
        """Check if the termination condition has been reached"""
        return False

    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
        self._count += 1
        if self._count == self._raise_on_count:
            raise ValueError("I am a flaky termination...")
        return None

    async def reset(self) -> None:
        pass


class _UnknownMessageType(BaseChatMessage):
    content: str

    def to_model_message(self) -> UserMessage:
        raise NotImplementedError("This message type is not supported.")

    def to_model_text(self) -> str:
        raise NotImplementedError("This message type is not supported.")

    def to_text(self) -> str:
        raise NotImplementedError("This message type is not supported.")

    def dump(self) -> Mapping[str, Any]:
        return {}

    @classmethod
    def load(cls, data: Mapping[str, Any]) -> "_UnknownMessageType":
        return cls(**data)


class _UnknownMessageTypeAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (_UnknownMessageType,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(chat_message=_UnknownMessageType(content="Unknown message type", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


class _StopAgent(_EchoAgent):
    def __init__(self, name: str, description: str, *, stop_at: int = 1) -> None:
        super().__init__(name, description)
        self._count = 0
        self._stop_at = stop_at

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage, StopMessage)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        self._count += 1
        if self._count < self._stop_at:
            return await super().on_messages(messages, cancellation_token)
        return Response(chat_message=StopMessage(content="TERMINATE", source=self.name))


def _pass_function(input: str) -> str:
    return "pass"


class _InputTask1(BaseModel):
    task: str
    data: List[str]


class _InputTask2(BaseModel):
    task: str
    data: str


TaskType = str | List[BaseChatMessage] | BaseChatMessage


@pytest_asyncio.fixture(params=["single_threaded", "embedded"])  # type: ignore
async def runtime(request: pytest.FixtureRequest) -> AsyncGenerator[AgentRuntime | None, None]:
    if request.param == "single_threaded":
        runtime = SingleThreadedAgentRuntime()
        runtime.start()
        yield runtime
        await runtime.stop()
    elif request.param == "embedded":
        yield None


@pytest.mark.asyncio
async def test_round_robin_group_chat(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = AssistantAgent(
            "coding_assistant",
            model_client=model_client,
        )
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat(
            participants=[coding_assistant_agent, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
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
        for i in range(len(expected_messages)):
            produced_message = result.messages[i]
            assert isinstance(produced_message, TextMessage)
            content = produced_message.content.replace("\r\n", "\n").rstrip("\n")
            assert content == expected_messages[i]

        assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

        # Test streaming with default output_task_messages=True.
        model_client.reset()
        await team.reset()
        streamed_messages: List[BaseAgentEvent | BaseChatMessage] = []
        final_stream_result: TaskResult | None = None
        async for message in team.run_stream(
            task="Write a program that prints 'Hello, world!'",
        ):
            if isinstance(message, TaskResult):
                final_stream_result = message
            else:
                streamed_messages.append(message)
        assert final_stream_result is not None
        assert compare_task_results(final_stream_result, result)
        # Verify streamed messages match the complete result.messages
        assert len(streamed_messages) == len(result.messages)
        for streamed_msg, expected_msg in zip(streamed_messages, result.messages, strict=False):
            assert compare_messages(streamed_msg, expected_msg)

        # Test message input.
        # Text message.
        model_client.reset()
        await team.reset()
        result_2 = await team.run(
            task=TextMessage(content="Write a program that prints 'Hello, world!'", source="user")
        )
        assert compare_task_results(result, result_2)

        # Test multi-modal message.
        model_client.reset()
        await team.reset()
        task = MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")
        result_2 = await team.run(task=task)
        assert isinstance(result.messages[0], TextMessage)
        assert isinstance(result_2.messages[0], MultiModalMessage)
        assert result.messages[0].content == task.content[0]
        assert len(result.messages[1:]) == len(result_2.messages[1:])
        for i in range(1, len(result.messages)):
            assert compare_messages(result.messages[i], result_2.messages[i])


@pytest.mark.asyncio
async def test_round_robin_group_chat_output_task_messages_false(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = AssistantAgent(
            "coding_assistant",
            model_client=model_client,
        )
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat(
            participants=[coding_assistant_agent, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
        )
        result = await team.run(
            task="Write a program that prints 'Hello, world!'",
            output_task_messages=False,
        )
        expected_messages = [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "Hello, world!",
            "TERMINATE",
        ]
        for i in range(len(expected_messages)):
            produced_message = result.messages[i]
            assert isinstance(produced_message, TextMessage)
            content = produced_message.content.replace("\r\n", "\n").rstrip("\n")
            assert content == expected_messages[i]

        assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

        # Test streaming with output_task_messages=False.
        model_client.reset()
        await team.reset()
        streamed_messages: List[BaseAgentEvent | BaseChatMessage] = []
        final_stream_result: TaskResult | None = None
        async for message in team.run_stream(
            task="Write a program that prints 'Hello, world!'",
            output_task_messages=False,
        ):
            if isinstance(message, TaskResult):
                final_stream_result = message
            else:
                streamed_messages.append(message)
        assert final_stream_result is not None
        assert compare_task_results(final_stream_result, result)
        # Verify streamed messages match the complete result.messages excluding the first task message
        assert len(streamed_messages) == len(result.messages)  # Exclude task message
        for streamed_msg, expected_msg in zip(streamed_messages, result.messages, strict=False):
            assert compare_messages(streamed_msg, expected_msg)

        # Test message input with output_task_messages=False.
        # Text message.
        model_client.reset()
        await team.reset()
        streamed_messages_2: List[BaseAgentEvent | BaseChatMessage] = []
        final_stream_result_2: TaskResult | None = None
        async for message in team.run_stream(
            task=TextMessage(content="Write a program that prints 'Hello, world!'", source="user"),
            output_task_messages=False,
        ):
            if isinstance(message, TaskResult):
                final_stream_result_2 = message
            else:
                streamed_messages_2.append(message)
        assert final_stream_result_2 is not None
        assert compare_task_results(final_stream_result_2, result)
        # Verify streamed messages match the complete result.messages excluding the first task message
        assert len(streamed_messages_2) == len(result.messages)
        for streamed_msg, expected_msg in zip(streamed_messages_2, result.messages, strict=False):
            assert compare_messages(streamed_msg, expected_msg)

        # Test multi-modal message with output_task_messages=False.
        model_client.reset()
        await team.reset()
        task = MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")
        streamed_messages_3: List[BaseAgentEvent | BaseChatMessage] = []
        final_stream_result_3: TaskResult | None = None
        async for message in team.run_stream(task=task, output_task_messages=False):
            if isinstance(message, TaskResult):
                final_stream_result_3 = message
            else:
                streamed_messages_3.append(message)
        assert final_stream_result_3 is not None
        # Verify streamed messages exclude the task message
        assert len(streamed_messages_3) == len(final_stream_result_3.messages)
        for streamed_msg, expected_msg in zip(streamed_messages_3, final_stream_result_3.messages, strict=False):
            assert compare_messages(streamed_msg, expected_msg)


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_team_event(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = AssistantAgent(
            "coding_assistant",
            model_client=model_client,
        )
        termination = TextMentionTermination("TERMINATE")
        team = RoundRobinGroupChat(
            participants=[coding_assistant_agent, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
            emit_team_events=True,
        )
        result = await team.run(
            task="Write a program that prints 'Hello, world!'",
        )
        assert len(result.messages) == 7
        assert isinstance(result.messages[0], TextMessage)
        assert isinstance(result.messages[1], SelectSpeakerEvent)
        assert isinstance(result.messages[2], TextMessage)
        assert isinstance(result.messages[3], SelectSpeakerEvent)
        assert isinstance(result.messages[4], TextMessage)
        assert isinstance(result.messages[5], SelectSpeakerEvent)
        assert isinstance(result.messages[6], TextMessage)

        # Test streaming with default output_task_messages=True.
        model_client.reset()
        await team.reset()
        streamed_messages: List[BaseAgentEvent | BaseChatMessage] = []
        final_stream_result: TaskResult | None = None
        async for message in team.run_stream(
            task="Write a program that prints 'Hello, world!'",
        ):
            if isinstance(message, TaskResult):
                final_stream_result = message
            else:
                streamed_messages.append(message)
        assert final_stream_result is not None
        assert compare_task_results(final_stream_result, result)
        # Verify streamed messages match the complete result.messages
        assert len(streamed_messages) == len(result.messages)
        for streamed_msg, expected_msg in zip(streamed_messages, result.messages, strict=False):
            assert compare_messages(streamed_msg, expected_msg)

        # Test multi-modal message.
        model_client.reset()
        await team.reset()
        task = MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")
        result_2 = await team.run(task=task)
        assert isinstance(result.messages[0], TextMessage)
        assert isinstance(result_2.messages[0], MultiModalMessage)
        assert result.messages[0].content == task.content[0]
        assert len(result.messages[1:]) == len(result_2.messages[1:])
        for i in range(1, len(result.messages)):
            assert compare_messages(result.messages[i], result_2.messages[i])


@pytest.mark.asyncio
async def test_round_robin_group_chat_unknown_task_message_type(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient([])
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask2]],
    )
    with pytest.raises(ValueError, match=r"Message type .*StructuredMessage\[_InputTask1\].* is not registered"):
        await team1.run(
            task=StructuredMessage[_InputTask1](
                content=_InputTask1(task="Write a program that prints 'Hello, world!'", data=["a", "b", "c"]),
                source="user",
            )
        )


@pytest.mark.asyncio
async def test_round_robin_group_chat_unknown_agent_message_type() -> None:
    model_client = ReplayChatCompletionClient(["Hello"])
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = _UnknownMessageTypeAgent("agent2", "I am an unknown message type agent")
    termination = TextMentionTermination("TERMINATE")
    team1 = RoundRobinGroupChat(participants=[agent1, agent2], termination_condition=termination)
    with pytest.raises(RuntimeError, match=".* Message type .*UnknownMessageType.* not registered"):
        await team1.run(task=TextMessage(content="Write a program that prints 'Hello, world!'", source="user"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task",
    [
        "Write a program that prints 'Hello, world!'",
        [TextMessage(content="Write a program that prints 'Hello, world!'", source="user")],
        [MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")],
        [
            StructuredMessage[_InputTask1](
                content=_InputTask1(task="Write a program that prints 'Hello, world!'", data=["a", "b", "c"]),
                source="user",
            ),
            StructuredMessage[_InputTask2](
                content=_InputTask2(task="Write a program that prints 'Hello, world!'", data="a"), source="user"
            ),
        ],
    ],
    ids=["text", "text_message", "multi_modal_message", "structured_message"],
)
async def test_round_robin_group_chat_state(task: TaskType, runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["No facts", "No plan", "print('Hello, world!')", "TERMINATE"],
    )
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team1.run(task=task)
    state = await team1.save_state()

    agent3 = AssistantAgent("agent1", model_client=model_client)
    agent4 = AssistantAgent("agent2", model_client=model_client)
    team2 = RoundRobinGroupChat(
        participants=[agent3, agent4],
        termination_condition=termination,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2

    agent1_model_ctx_messages = await agent1._model_context.get_messages()  # pyright: ignore
    agent2_model_ctx_messages = await agent2._model_context.get_messages()  # pyright: ignore
    agent3_model_ctx_messages = await agent3._model_context.get_messages()  # pyright: ignore
    agent4_model_ctx_messages = await agent4._model_context.get_messages()  # pyright: ignore
    assert agent3_model_ctx_messages == agent1_model_ctx_messages
    assert agent4_model_ctx_messages == agent2_model_ctx_messages
    manager_1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team1._group_chat_manager_name}_{team1._team_id}", team1._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._current_turn == manager_2._current_turn  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_tools(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", name="pass", arguments=json.dumps({"input": "pass"}))],
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Hello",
            "TERMINATE",
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "structured_output": True,
        },
    )
    tool = FunctionTool(_pass_function, name="pass", description="pass function")
    tool_use_agent = AssistantAgent("tool_use_agent", model_client=model_client, tools=[tool])
    echo_agent = _EchoAgent("echo_agent", description="echo agent")
    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat(
        participants=[tool_use_agent, echo_agent], termination_condition=termination, runtime=runtime
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 8
    assert isinstance(result.messages[0], TextMessage)  # task
    assert isinstance(result.messages[1], ToolCallRequestEvent)  # tool call
    assert isinstance(result.messages[2], ToolCallExecutionEvent)  # tool call result
    assert isinstance(result.messages[3], ToolCallSummaryMessage)  # tool use agent response
    assert result.messages[3].content == "pass"  #  ensure the tool call was executed
    assert isinstance(result.messages[4], TextMessage)  # echo agent response
    assert isinstance(result.messages[5], TextMessage)  # tool use agent response
    assert isinstance(result.messages[6], TextMessage)  # echo agent response
    assert isinstance(result.messages[7], TextMessage)  # tool use agent response, that has TERMINATE
    assert result.messages[7].content == "TERMINATE"

    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    await tool_use_agent._model_context.clear()  # pyright: ignore
    model_client.reset()
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test Console.
    await tool_use_agent._model_context.clear()  # pyright: ignore
    model_client.reset()
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert compare_task_results(result2, result)


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_resume_and_reset(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    termination = MaxMessageTermination(3)
    team = RoundRobinGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4], termination_condition=termination, runtime=runtime
    )
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
async def test_round_robin_group_chat_with_exception_raised_from_agent(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _FlakyAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    termination = MaxMessageTermination(3)
    team = RoundRobinGroupChat(
        participants=[agent_1, agent_2, agent_3],
        termination_condition=termination,
        runtime=runtime,
    )

    with pytest.raises(RuntimeError, match="I am a flaky agent..."):
        await team.run(
            task="Write a program that prints 'Hello, world!'",
        )


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_exception_raised_from_termination_condition(
    runtime: AgentRuntime | None,
) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _FlakyAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    team = RoundRobinGroupChat(
        participants=[agent_1, agent_2, agent_3],
        termination_condition=_FlakyTermination(raise_on_count=1),
        runtime=runtime,
    )

    with pytest.raises(Exception, match="I am a flaky termination..."):
        await team.run(
            task="Write a program that prints 'Hello, world!'",
        )


@pytest.mark.asyncio
async def test_round_robin_group_chat_max_turn(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    team = RoundRobinGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], max_turns=3, runtime=runtime)
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
async def test_round_robin_group_chat_cancellation(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")
    # Set max_turns to a large number to avoid stopping due to max_turns before cancellation.
    team = RoundRobinGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], max_turns=1000, runtime=runtime)
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

    # Still can run again and finish the task.
    result = await team.run()
    assert result.stop_reason is not None and result.stop_reason == "Maximum number of turns 1000 reached."


@pytest.mark.asyncio
async def test_selector_group_chat(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "agent3",
            "agent2",
            "agent1",
            "agent2",
            "agent1",
        ]
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=2)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 6
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent3"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.messages[4].source == "agent2"
    assert result.messages[5].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test Console.
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert compare_task_results(result2, result)


@pytest.mark.asyncio
async def test_selector_group_chat_with_model_context(runtime: AgentRuntime | None) -> None:
    buffered_context = BufferedChatCompletionContext(buffer_size=5)
    await buffered_context.add_message(UserMessage(content="[User] Prefilled message", source="user"))

    selector_group_chat_model_client = ReplayChatCompletionClient(
        ["agent2", "agent1", "agent1", "agent2", "agent1", "agent2", "agent1"]
    )
    agent_one_model_client = ReplayChatCompletionClient(
        ["[Agent One] First generation", "[Agent One] Second generation", "[Agent One] Third generation", "TERMINATE"]
    )
    agent_two_model_client = ReplayChatCompletionClient(
        ["[Agent Two] First generation", "[Agent Two] Second generation", "[Agent Two] Third generation"]
    )

    agent1 = AssistantAgent("agent1", model_client=agent_one_model_client, description="Assistant agent 1")
    agent2 = AssistantAgent("agent2", model_client=agent_two_model_client, description="Assistant agent 2")

    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=selector_group_chat_model_client,
        termination_condition=termination,
        runtime=runtime,
        emit_team_events=True,
        allow_repeated_speaker=True,
        model_context=buffered_context,
    )
    await team.run(
        task="[GroupChat] Task",
    )

    messages_to_check = [
        "user: [User] Prefilled message",
        "user: [GroupChat] Task",
        "agent2: [Agent Two] First generation",
        "agent1: [Agent One] First generation",
        "agent1: [Agent One] Second generation",
        "agent2: [Agent Two] Second generation",
        "agent1: [Agent One] Third generation",
        "agent2: [Agent Two] Third generation",
    ]

    create_calls: List[Dict[str, Any]] = selector_group_chat_model_client.create_calls
    for idx, call in enumerate(create_calls):
        messages = call["messages"]
        prompt = messages[0].content
        prompt_lines = prompt.split("\n")
        chat_history = [value for value in messages_to_check[max(0, idx - 3) : idx + 2]]
        assert all(
            line.strip() in prompt_lines for line in chat_history
        ), f"Expected all lines {chat_history} to be in prompt, but got {prompt_lines}"


@pytest.mark.asyncio
async def test_selector_group_chat_with_team_event(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["agent3", "agent2", "agent1", "agent2", "agent1"],
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=2)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
        emit_team_events=True,
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 11
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], SelectSpeakerEvent)
    assert isinstance(result.messages[2], TextMessage)
    assert isinstance(result.messages[3], SelectSpeakerEvent)
    assert isinstance(result.messages[4], TextMessage)
    assert isinstance(result.messages[5], SelectSpeakerEvent)
    assert isinstance(result.messages[6], TextMessage)
    assert isinstance(result.messages[7], SelectSpeakerEvent)
    assert isinstance(result.messages[8], TextMessage)
    assert isinstance(result.messages[9], SelectSpeakerEvent)
    assert isinstance(result.messages[10], StopMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].content == ["agent3"]
    assert result.messages[2].source == "agent3"
    assert result.messages[3].content == ["agent2"]
    assert result.messages[4].source == "agent2"
    assert result.messages[5].content == ["agent1"]
    assert result.messages[6].source == "agent1"
    assert result.messages[7].content == ["agent2"]
    assert result.messages[8].source == "agent2"
    assert result.messages[9].content == ["agent1"]
    assert result.messages[10].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task",
    [
        "Write a program that prints 'Hello, world!'",
        [TextMessage(content="Write a program that prints 'Hello, world!'", source="user")],
        [MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")],
        [
            StructuredMessage[_InputTask1](
                content=_InputTask1(task="Write a program that prints 'Hello, world!'", data=["a", "b", "c"]),
                source="user",
            ),
            StructuredMessage[_InputTask2](
                content=_InputTask2(task="Write a program that prints 'Hello, world!'", data="a"), source="user"
            ),
        ],
    ],
    ids=["text", "text_message", "multi_modal_message", "structured_message"],
)
async def test_selector_group_chat_state(task: TaskType, runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["agent1", "No facts", "agent2", "No plan", "agent1", "print('Hello, world!')", "agent2", "TERMINATE"],
    )
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = SelectorGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        model_client=model_client,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team1.run(task=task)
    state = await team1.save_state()

    agent3 = AssistantAgent("agent1", model_client=model_client)
    agent4 = AssistantAgent("agent2", model_client=model_client)
    team2 = SelectorGroupChat(
        participants=[agent3, agent4],
        termination_condition=termination,
        model_client=model_client,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2

    agent1_model_ctx_messages = await agent1._model_context.get_messages()  # pyright: ignore
    agent2_model_ctx_messages = await agent2._model_context.get_messages()  # pyright: ignore
    agent3_model_ctx_messages = await agent3._model_context.get_messages()  # pyright: ignore
    agent4_model_ctx_messages = await agent4._model_context.get_messages()  # pyright: ignore
    assert agent3_model_ctx_messages == agent1_model_ctx_messages
    assert agent4_model_ctx_messages == agent2_model_ctx_messages
    manager_1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team1._group_chat_manager_name}_{team1._team_id}", team1._team_id),  # pyright: ignore
        SelectorGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        SelectorGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._previous_speaker == manager_2._previous_speaker  # pyright: ignore


@pytest.mark.asyncio
async def test_selector_group_chat_two_speakers(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(["agent2"])

    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=2)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        model_client=model_client,
        runtime=runtime,
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )
    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent1"
    assert result.messages[3].source == "agent2"
    assert result.messages[4].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    async for message in team.run_stream(task="Write a program that prints 'Hello, world!'"):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test Console.
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert compare_task_results(result2, result)


@pytest.mark.asyncio
async def test_selector_group_chat_two_speakers_allow_repeated(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            "agent2",
            "agent2",
            "agent1",
        ]
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=1)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    termination = TextMentionTermination("TERMINATE")
    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
        allow_repeated_speaker=True,
        runtime=runtime,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    async for message in team.run_stream(task="Write a program that prints 'Hello, world!'"):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test Console.
    model_client.reset()
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert compare_task_results(result2, result)


@pytest.mark.asyncio
async def test_selector_group_chat_succcess_after_2_attempts(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["agent2, agent3", "agent2"],
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=1)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=model_client,
        max_turns=1,
        runtime=runtime,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 2
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"


@pytest.mark.asyncio
async def test_selector_group_chat_fall_back_to_first_after_3_attempts(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            "agent2, agent3",  # Multiple speakers
            "agent5",  # Non-existent speaker
            "agent3, agent1",  # Multiple speakers
        ]
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=1)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=model_client,
        max_turns=1,
        runtime=runtime,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 2
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent1"


@pytest.mark.asyncio
async def test_selector_group_chat_fall_back_to_previous_after_3_attempts(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["agent2", "agent2", "agent2", "agent2"],
    )
    agent1 = _StopAgent("agent1", description="echo agent 1", stop_at=1)
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3],
        model_client=model_client,
        max_turns=2,
        runtime=runtime,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 3
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent2"


@pytest.mark.asyncio
async def test_selector_group_chat_custom_selector(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(["agent3"])
    agent1 = _EchoAgent("agent1", description="echo agent 1")
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    agent4 = _EchoAgent("agent4", description="echo agent 4")

    def _select_agent(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
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
        model_client=model_client,
        selector_func=_select_agent,
        termination_condition=termination,
        runtime=runtime,
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


@pytest.mark.asyncio
async def test_selector_group_chat_custom_candidate_func(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(["agent3"])
    agent1 = _EchoAgent("agent1", description="echo agent 1")
    agent2 = _EchoAgent("agent2", description="echo agent 2")
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    agent4 = _EchoAgent("agent4", description="echo agent 4")

    def _candidate_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str]:
        if len(messages) == 0:
            return ["agent1"]
        elif messages[-1].source == "agent1":
            return ["agent2"]
        elif messages[-1].source == "agent2":
            return ["agent2", "agent3"]  # will generate agent3
        elif messages[-1].source == "agent3":
            return ["agent4"]
        else:
            return ["agent1"]

    termination = MaxMessageTermination(6)
    team = SelectorGroupChat(
        participants=[agent1, agent2, agent3, agent4],
        model_client=model_client,
        candidate_func=_candidate_func,
        termination_condition=termination,
        runtime=runtime,
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
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (HandoffMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(
            chat_message=HandoffMessage(
                content=f"Transferred to {self._next_agent}.", target=self._next_agent, source=self.name
            )
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


@pytest.mark.asyncio
async def test_swarm_handoff(runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    termination = MaxMessageTermination(6)
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination, runtime=runtime)
    result = await team.run(task="task")
    assert len(result.messages) == 6
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert isinstance(result.messages[2], HandoffMessage)
    assert isinstance(result.messages[3], HandoffMessage)
    assert isinstance(result.messages[4], HandoffMessage)
    assert isinstance(result.messages[5], HandoffMessage)
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
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    stream = team.run_stream(task="task")
    async for message in stream:
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test save and load.
    state = await team.save_state()
    first_agent2 = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent2 = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent2 = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")
    team2 = Swarm([second_agent2, first_agent2, third_agent2], termination_condition=termination, runtime=runtime)
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2
    manager_1 = await team._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team._group_chat_manager_name}_{team._team_id}", team._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._current_speaker == manager_2._current_speaker  # pyright: ignore


@pytest.mark.asyncio
async def test_swarm_handoff_with_team_events(runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    termination = MaxMessageTermination(6)
    team = Swarm(
        [second_agent, first_agent, third_agent],
        termination_condition=termination,
        runtime=runtime,
        emit_team_events=True,
    )
    result = await team.run(task="task")
    assert len(result.messages) == 11
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], SelectSpeakerEvent)
    assert isinstance(result.messages[2], HandoffMessage)
    assert isinstance(result.messages[3], SelectSpeakerEvent)
    assert isinstance(result.messages[4], HandoffMessage)
    assert isinstance(result.messages[5], SelectSpeakerEvent)
    assert isinstance(result.messages[6], HandoffMessage)
    assert isinstance(result.messages[7], SelectSpeakerEvent)
    assert isinstance(result.messages[8], HandoffMessage)
    assert isinstance(result.messages[9], SelectSpeakerEvent)
    assert isinstance(result.messages[10], HandoffMessage)
    assert result.messages[0].content == "task"
    assert result.messages[1].content == ["second_agent"]
    assert result.messages[2].content == "Transferred to third_agent."
    assert result.messages[3].content == ["third_agent"]
    assert result.messages[4].content == "Transferred to first_agent."
    assert result.messages[5].content == ["first_agent"]
    assert result.messages[6].content == "Transferred to second_agent."
    assert result.messages[7].content == ["second_agent"]
    assert result.messages[8].content == "Transferred to third_agent."
    assert result.messages[9].content == ["third_agent"]
    assert result.messages[10].content == "Transferred to first_agent."
    assert (
        result.stop_reason is not None
        and result.stop_reason == "Maximum number of messages 6 reached, current message count: 6"
    )

    # Test streaming.
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    stream = team.run_stream(task="task")
    async for message in stream:
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task",
    [
        "Write a program that prints 'Hello, world!'",
        [TextMessage(content="Write a program that prints 'Hello, world!'", source="user")],
        [MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")],
        [
            StructuredMessage[_InputTask1](
                content=_InputTask1(task="Write a program that prints 'Hello, world!'", data=["a", "b", "c"]),
                source="user",
            ),
            StructuredMessage[_InputTask2](
                content=_InputTask2(task="Write a program that prints 'Hello, world!'", data="a"), source="user"
            ),
        ],
    ],
    ids=["text", "text_message", "multi_modal_message", "structured_message"],
)
async def test_swarm_handoff_state(task: TaskType, runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    termination = MaxMessageTermination(6)
    team1 = Swarm(
        [second_agent, first_agent, third_agent],
        termination_condition=termination,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team1.run(task=task)
    state = await team1.save_state()

    first_agent2 = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent2 = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent2 = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")
    team2 = Swarm(
        [second_agent2, first_agent2, third_agent2],
        termination_condition=termination,
        runtime=runtime,
        custom_message_types=[StructuredMessage[_InputTask1], StructuredMessage[_InputTask2]],
    )
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2

    manager_1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team1._group_chat_manager_name}_{team1._team_id}", team1._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        SwarmGroupChatManager,  # pyright: ignore
    )
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._current_speaker == manager_2._current_speaker  # pyright: ignore


@pytest.mark.asyncio
async def test_swarm_handoff_using_tool_calls(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", name="handoff_to_agent2", arguments=json.dumps({}))],
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Hello",
            "TERMINATE",
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "structured_output": True,
        },
    )
    agent1 = AssistantAgent(
        "agent1",
        model_client=model_client,
        handoffs=[Handoff(target="agent2", name="handoff_to_agent2", message="handoff to agent2")],
    )
    agent2 = _HandOffAgent("agent2", description="agent 2", next_agent="agent1")
    termination = TextMentionTermination("TERMINATE")
    team = Swarm([agent1, agent2], termination_condition=termination, runtime=runtime)
    result = await team.run(task="task")
    assert len(result.messages) == 7
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "task"
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert isinstance(result.messages[3], HandoffMessage)
    assert isinstance(result.messages[4], HandoffMessage)
    assert isinstance(result.messages[5], TextMessage)
    assert isinstance(result.messages[6], TextMessage)
    assert result.messages[3].content == "handoff to agent2"
    assert result.messages[4].content == "Transferred to agent1."
    assert result.messages[5].content == "Hello"
    assert result.messages[6].content == "TERMINATE"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    await agent1._model_context.clear()  # pyright: ignore
    model_client.reset()
    result_index = 0  # Include task message in result since output_task_messages=True by default
    await team.reset()
    stream = team.run_stream(task="task")
    async for message in stream:
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test Console
    await agent1._model_context.clear()  # pyright: ignore
    model_client.reset()
    await team.reset()
    result2 = await Console(team.run_stream(task="task"))
    assert compare_task_results(result2, result)


@pytest.mark.asyncio
async def test_swarm_pause_and_resume(runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    team = Swarm([second_agent, first_agent, third_agent], max_turns=1, runtime=runtime)
    result = await team.run(task="task")
    assert len(result.messages) == 2
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."

    # Resume with a new task.
    result = await team.run(task="new task")
    assert len(result.messages) == 2
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert result.messages[0].content == "new task"
    assert result.messages[1].content == "Transferred to first_agent."

    # Resume with the same task.
    result = await team.run()
    assert len(result.messages) == 1
    assert isinstance(result.messages[0], HandoffMessage)
    assert result.messages[0].content == "Transferred to second_agent."


@pytest.mark.asyncio
async def test_swarm_with_parallel_tool_calls(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[
                    FunctionCall(id="1", name="tool1", arguments="{}"),
                    FunctionCall(id="2", name="tool2", arguments="{}"),
                    FunctionCall(id="3", name="handoff_to_agent2", arguments=json.dumps({})),
                ],
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Hello",
            "TERMINATE",
        ],
        model_info={
            "family": "gpt-4.1-nano",
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "structured_output": True,
        },
    )

    expected_handoff_context: List[LLMMessage] = [
        AssistantMessage(
            source="agent1",
            content=[
                FunctionCall(id="1", name="tool1", arguments="{}"),
                FunctionCall(id="2", name="tool2", arguments="{}"),
            ],
        ),
        FunctionExecutionResultMessage(
            content=[
                FunctionExecutionResult(content="tool1", call_id="1", is_error=False, name="tool1"),
                FunctionExecutionResult(content="tool2", call_id="2", is_error=False, name="tool2"),
            ]
        ),
    ]

    def tool1() -> str:
        return "tool1"

    def tool2() -> str:
        return "tool2"

    agent1 = AssistantAgent(
        "agent1",
        model_client=model_client,
        handoffs=[Handoff(target="agent2", name="handoff_to_agent2", message="handoff to agent2")],
        tools=[tool1, tool2],
    )
    agent2 = AssistantAgent(
        "agent2",
        model_client=model_client,
    )
    termination = TextMentionTermination("TERMINATE")
    team = Swarm([agent1, agent2], termination_condition=termination, runtime=runtime)
    result = await team.run(task="task")
    assert len(result.messages) == 6
    assert compare_messages(result.messages[0], TextMessage(content="task", source="user"))
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert compare_messages(
        result.messages[3],
        HandoffMessage(
            content="handoff to agent2",
            target="agent2",
            source="agent1",
            context=expected_handoff_context,
        ),
    )
    assert isinstance(result.messages[4], TextMessage)
    assert result.messages[4].content == "Hello"
    assert result.messages[4].source == "agent2"
    assert isinstance(result.messages[5], TextMessage)
    assert result.messages[5].content == "TERMINATE"
    assert result.messages[5].source == "agent2"

    # Verify the tool calls are in agent2's context.
    agent2_model_ctx_messages = await agent2._model_context.get_messages()  # pyright: ignore
    assert agent2_model_ctx_messages[0] == UserMessage(content="task", source="user")
    assert agent2_model_ctx_messages[1] == expected_handoff_context[0]
    assert agent2_model_ctx_messages[2] == expected_handoff_context[1]


@pytest.mark.asyncio
async def test_swarm_with_handoff_termination(runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    # Handoff to an existing agent.
    termination = HandoffTermination(target="third_agent")
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination, runtime=runtime)
    # Start
    result = await team.run(task="task")
    assert len(result.messages) == 2
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert result.messages[0].content == "task"
    assert result.messages[1].content == "Transferred to third_agent."
    # Resume existing.
    result = await team.run()
    assert len(result.messages) == 3
    assert isinstance(result.messages[0], HandoffMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert isinstance(result.messages[2], HandoffMessage)
    assert result.messages[0].content == "Transferred to first_agent."
    assert result.messages[1].content == "Transferred to second_agent."
    assert result.messages[2].content == "Transferred to third_agent."
    # Resume new task.
    result = await team.run(task="new task")
    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert isinstance(result.messages[2], HandoffMessage)
    assert isinstance(result.messages[3], HandoffMessage)
    assert result.messages[0].content == "new task"
    assert result.messages[1].content == "Transferred to first_agent."
    assert result.messages[2].content == "Transferred to second_agent."
    assert result.messages[3].content == "Transferred to third_agent."

    # Handoff to a non-existing agent.
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="non_existing_agent")
    termination = HandoffTermination(target="non_existing_agent")
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination, runtime=runtime)
    # Start
    result = await team.run(task="task")
    assert len(result.messages) == 3
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert isinstance(result.messages[2], HandoffMessage)
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
    assert isinstance(result.messages[0], HandoffMessage)
    assert isinstance(result.messages[1], HandoffMessage)
    assert isinstance(result.messages[2], HandoffMessage)
    assert isinstance(result.messages[3], HandoffMessage)
    assert result.messages[0].content == "Handoff to first_agent."
    assert result.messages[1].content == "Transferred to second_agent."
    assert result.messages[2].content == "Transferred to third_agent."
    assert result.messages[3].content == "Transferred to non_existing_agent."


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_message_list(runtime: AgentRuntime | None) -> None:
    # Create a simple team with echo agents
    agent1 = _EchoAgent("Agent1", "First agent")
    agent2 = _EchoAgent("Agent2", "Second agent")
    termination = MaxMessageTermination(4)  # Stop after 4 messages
    team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination, runtime=runtime)

    # Create a list of messages
    messages: List[BaseChatMessage] = [
        TextMessage(content="Message 1", source="user"),
        TextMessage(content="Message 2", source="user"),
        TextMessage(content="Message 3", source="user"),
    ]

    # Run the team with the message list
    result = await team.run(task=messages)

    # Verify the messages were processed in order
    assert len(result.messages) == 4  # Initial messages + echo until termination
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], TextMessage)
    assert isinstance(result.messages[2], TextMessage)
    assert isinstance(result.messages[3], TextMessage)
    assert result.messages[0].content == "Message 1"  # First message
    assert result.messages[1].content == "Message 2"  # Second message
    assert result.messages[2].content == "Message 3"  # Third message
    assert result.messages[3].content == "Message 1"  # Echo from first agent
    assert result.stop_reason == "Maximum number of messages 4 reached, current message count: 4"

    # Test with streaming
    await team.reset()
    result_index = 0  # Include the 3 task messages in result since output_task_messages=True by default
    async for message in team.run_stream(task=messages):
        if isinstance(message, TaskResult):
            assert compare_task_results(message, result)
        else:
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Test with invalid message list
    with pytest.raises(ValueError, match="All messages in task list must be valid BaseChatMessage types"):
        await team.run(task=["not a message"])  # type: ignore[list-item, arg-type]  # intentionally testing invalid input

    # Test with empty message list
    with pytest.raises(ValueError, match="Task list cannot be empty"):
        await team.run(task=[])


@pytest.mark.asyncio
async def test_declarative_groupchats_with_config(runtime: AgentRuntime | None) -> None:
    # Create basic agents and components for testing
    agent1 = AssistantAgent(
        "agent_1",
        model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano-2025-04-14", api_key=""),
        handoffs=["agent_2"],
    )
    agent2 = AssistantAgent(
        "agent_2", model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano-2025-04-14", api_key="")
    )
    termination = MaxMessageTermination(4)
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano-2025-04-14", api_key="")

    # Test round robin - verify config is preserved
    round_robin = RoundRobinGroupChat(participants=[agent1, agent2], termination_condition=termination, max_turns=5)
    config = round_robin.dump_component()
    loaded = RoundRobinGroupChat.load_component(config)
    assert loaded.dump_component() == config

   

    # Test selector group chat - verify config is preserved
    selector_prompt = "Custom selector prompt with {roles}, {participants}, {history}"
    selector = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
        max_turns=10,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True,
        runtime=runtime,
    )
    selector_config = selector.dump_component()
    selector_loaded = SelectorGroupChat.load_component(selector_config)
    assert selector_loaded.dump_component() == selector_config

    # Test swarm with handoff termination
    handoff_termination = HandoffTermination(target="Agent2")
    swarm = Swarm(
        participants=[agent1, agent2], termination_condition=handoff_termination, max_turns=5, runtime=runtime
    )
    swarm_config = swarm.dump_component()
    swarm_loaded = Swarm.load_component(swarm_config)
    assert swarm_loaded.dump_component() == swarm_config

    # Test MagenticOne with custom parameters
    magentic = MagenticOneGroupChat(
        participants=[agent1],
        model_client=model_client,
        max_turns=15,
        max_stalls=5,
        final_answer_prompt="Custom prompt",
        runtime=runtime,
    )
    magentic_config = magentic.dump_component()
    magentic_loaded = MagenticOneGroupChat.load_component(magentic_config)
    assert magentic_loaded.dump_component() == magentic_config

    # Verify component types are correctly set for each
    for team in [loaded, selector, swarm, magentic]:
        assert team.component_type == "team"

    # Verify provider strings are correctly set
    assert round_robin.dump_component().provider == "autogen_agentchat.teams.RoundRobinGroupChat"
    assert selector.dump_component().provider == "autogen_agentchat.teams.SelectorGroupChat"
    assert swarm.dump_component().provider == "autogen_agentchat.teams.Swarm"
    assert magentic.dump_component().provider == "autogen_agentchat.teams.MagenticOneGroupChat"


class _StructuredContent(BaseModel):
    message: str


class _StructuredAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._message = _StructuredContent(message="Structured hello")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (StructuredMessage[_StructuredContent],)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(
            chat_message=StructuredMessage[_StructuredContent](
                source=self.name,
                content=self._message,
                format_string="Structured says: {message}",
            )
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


@pytest.mark.asyncio
async def test_message_type_auto_registration(runtime: AgentRuntime | None) -> None:
    agent1 = _StructuredAgent("structured", description="emits structured messages")
    agent2 = _EchoAgent("echo", description="echoes input")

    team = RoundRobinGroupChat(participants=[agent1, agent2], max_turns=2, runtime=runtime)

    result = await team.run(task="Say something structured")

    assert len(result.messages) == 3
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], StructuredMessage)
    assert isinstance(result.messages[2], TextMessage)
    assert result.messages[1].to_text() == "Structured says: Structured hello"


@pytest.mark.asyncio
async def test_structured_message_state_roundtrip(runtime: AgentRuntime | None) -> None:
    agent1 = _StructuredAgent("structured", description="sends structured")
    agent2 = _EchoAgent("echo", description="echoes")

    team1 = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=MaxMessageTermination(2),
        runtime=runtime,
    )

    await team1.run(task="Say something structured")
    state1 = await team1.save_state()

    # Recreate team without needing custom_message_types
    agent3 = _StructuredAgent("structured", description="sends structured")
    agent4 = _EchoAgent("echo", description="echoes")
    team2 = RoundRobinGroupChat(
        participants=[agent3, agent4],
        termination_condition=MaxMessageTermination(2),
        runtime=runtime,
    )

    await team2.load_state(state1)
    state2 = await team2.save_state()

    # Assert full state equality
    assert state1 == state2

    # Assert message thread content match
    manager1 = await team1._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team1._group_chat_manager_name}_{team1._team_id}", team1._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,
    )
    manager2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        RoundRobinGroupChatManager,
    )

    assert manager1._message_thread == manager2._message_thread  # pyright: ignore


@pytest.mark.asyncio
async def test_selector_group_chat_streaming(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["the agent should be agent2"],
    )
    agent2 = _StopAgent("agent2", description="stop agent 2", stop_at=0)
    agent3 = _EchoAgent("agent3", description="echo agent 3")
    termination = StopMessageTermination()
    team = SelectorGroupChat(
        participants=[agent2, agent3],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
        emit_team_events=True,
        model_client_streaming=True,
    )
    result = await team.run(
        task="Write a program that prints 'Hello, world!'",
    )

    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert isinstance(result.messages[1], SelectorEvent)
    assert isinstance(result.messages[2], SelectSpeakerEvent)
    assert isinstance(result.messages[3], StopMessage)

    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].content == "the agent should be agent2"
    assert result.messages[2].content == ["agent2"]
    assert result.messages[3].source == "agent2"
    assert result.stop_reason is not None and result.stop_reason == "Stop message received"

    # Test streaming
    await team.reset()
    model_client.reset()
    result_index = 0  # Include task message in result since output_task_messages=True by default
    streamed_chunks: List[str] = []
    final_result: TaskResult | None = None
    async for message in team.run_stream(
        task="Write a program that prints 'Hello, world!'",
    ):
        if isinstance(message, TaskResult):
            final_result = message
            assert compare_task_results(message, result)
        elif isinstance(message, ModelClientStreamingChunkEvent):
            streamed_chunks.append(message.content)
        else:
            if streamed_chunks:
                assert isinstance(message, SelectorEvent)
                assert message.content == "".join(streamed_chunks)
                streamed_chunks = []
            assert compare_messages(message, result.messages[result_index])
            result_index += 1

    # Verify we got the expected messages without relying on fragile ordering
    assert final_result is not None
    assert len(streamed_chunks) == 0  # All chunks should have been processed

    # Content-based verification instead of index-based
    # Note: The streaming test verifies the streaming behavior, not the final result content
