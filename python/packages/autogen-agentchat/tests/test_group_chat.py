import asyncio
import json
import logging
import tempfile
from typing import AsyncGenerator, List, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    AssistantAgent,
    BaseChatAgent,
    CodeExecutorAgent,
)
from autogen_agentchat.base import Handoff, Response, TaskResult
from autogen_agentchat.conditions import HandoffTermination, MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
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
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_group_chat.log"))


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

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


class _FlakyAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        raise ValueError("I am a flaky agent...")

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_message = None


class _StopAgent(_EchoAgent):
    def __init__(self, name: str, description: str, *, stop_at: int = 1) -> None:
        super().__init__(name, description)
        self._count = 0
        self._stop_at = stop_at

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage, StopMessage)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        self._count += 1
        if self._count < self._stop_at:
            return await super().on_messages(messages, cancellation_token)
        return Response(chat_message=StopMessage(content="TERMINATE", source=self.name))


def _pass_function(input: str) -> str:
    return "pass"


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
        # Normalize the messages to remove \r\n and any leading/trailing whitespace.
        normalized_messages = [
            msg.content.replace("\r\n", "\n").rstrip("\n") if isinstance(msg.content, str) else msg.content
            for msg in result.messages
        ]

        # Assert that all expected messages are in the collected messages
        assert normalized_messages == expected_messages

        assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

        # Test streaming.
        model_client.reset()
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
        model_client.reset()
        index = 0
        await team.reset()
        result_2 = await team.run(
            task=TextMessage(content="Write a program that prints 'Hello, world!'", source="user")
        )
        assert result == result_2

        # Test multi-modal message.
        model_client.reset()
        index = 0
        await team.reset()
        result_2 = await team.run(
            task=MultiModalMessage(content=["Write a program that prints 'Hello, world!'"], source="user")
        )
        assert result.messages[0].content == result_2.messages[0].content[0]
        assert result.messages[1:] == result_2.messages[1:]


@pytest.mark.asyncio
async def test_round_robin_group_chat_state(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["No facts", "No plan", "print('Hello, world!')", "TERMINATE"],
    )
    agent1 = AssistantAgent("agent1", model_client=model_client)
    agent2 = AssistantAgent("agent2", model_client=model_client)
    termination = TextMentionTermination("TERMINATE")
    team1 = RoundRobinGroupChat(participants=[agent1, agent2], termination_condition=termination, runtime=runtime)
    await team1.run(task="Write a program that prints 'Hello, world!'")
    state = await team1.save_state()

    agent3 = AssistantAgent("agent1", model_client=model_client)
    agent4 = AssistantAgent("agent2", model_client=model_client)
    team2 = RoundRobinGroupChat(participants=[agent3, agent4], termination_condition=termination, runtime=runtime)
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
        model_info={"family": "gpt-4o", "function_calling": True, "json_output": True, "vision": True},
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
    await tool_use_agent._model_context.clear()  # pyright: ignore
    model_client.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


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


# TODO: add runtime fixture for testing with custom runtime once the issue regarding
# hanging on exception is resolved.
@pytest.mark.asyncio
async def test_round_robin_group_chat_with_exception_raised() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _FlakyAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    termination = MaxMessageTermination(3)
    team = RoundRobinGroupChat(
        participants=[agent_1, agent_2, agent_3],
        termination_condition=termination,
    )

    with pytest.raises(ValueError, match="I am a flaky agent..."):
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
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


@pytest.mark.asyncio
async def test_selector_group_chat_state(runtime: AgentRuntime | None) -> None:
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
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent1"
    assert result.messages[3].source == "agent2"
    assert result.messages[4].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
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
    model_client.reset()
    agent1._count = 0  # pyright: ignore
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


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
    assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
    assert result.messages[1].source == "agent2"
    assert result.messages[2].source == "agent2"
    assert result.messages[3].source == "agent1"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    model_client.reset()
    index = 0
    await team.reset()
    async for message in team.run_stream(task="Write a program that prints 'Hello, world!'"):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
        index += 1

    # Test Console.
    model_client.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="Write a program that prints 'Hello, world!'"))
    assert result2 == result


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

    def _select_agent(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
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


class _HandOffAgent(BaseChatAgent):
    def __init__(self, name: str, description: str, next_agent: str) -> None:
        super().__init__(name, description)
        self._next_agent = next_agent

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (HandoffMessage,)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
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
        model_info={"family": "gpt-4o", "function_calling": True, "json_output": True, "vision": True},
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
    assert result.messages[0].content == "task"
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[3].content == "handoff to agent2"
    assert result.messages[4].content == "Transferred to agent1."
    assert result.messages[5].content == "Hello"
    assert result.messages[6].content == "TERMINATE"
    assert result.stop_reason is not None and result.stop_reason == "Text 'TERMINATE' mentioned"

    # Test streaming.
    await agent1._model_context.clear()  # pyright: ignore
    model_client.reset()
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
    await agent1._model_context.clear()  # pyright: ignore
    model_client.reset()
    index = 0
    await team.reset()
    result2 = await Console(team.run_stream(task="task"))
    assert result2 == result


@pytest.mark.asyncio
async def test_swarm_pause_and_resume(runtime: AgentRuntime | None) -> None:
    first_agent = _HandOffAgent("first_agent", description="first agent", next_agent="second_agent")
    second_agent = _HandOffAgent("second_agent", description="second agent", next_agent="third_agent")
    third_agent = _HandOffAgent("third_agent", description="third agent", next_agent="first_agent")

    team = Swarm([second_agent, first_agent, third_agent], max_turns=1, runtime=runtime)
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
        model_info={"family": "gpt-4o", "function_calling": True, "json_output": True, "vision": True},
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
    assert result.messages[0] == TextMessage(content="task", source="user")
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], ToolCallExecutionEvent)
    assert result.messages[3] == HandoffMessage(
        content="handoff to agent2",
        target="agent2",
        source="agent1",
        context=expected_handoff_context,
    )
    assert result.messages[4].content == "Hello"
    assert result.messages[4].source == "agent2"
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
    team = Swarm([second_agent, first_agent, third_agent], termination_condition=termination, runtime=runtime)
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


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_message_list(runtime: AgentRuntime | None) -> None:
    # Create a simple team with echo agents
    agent1 = _EchoAgent("Agent1", "First agent")
    agent2 = _EchoAgent("Agent2", "Second agent")
    termination = MaxMessageTermination(4)  # Stop after 4 messages
    team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination, runtime=runtime)

    # Create a list of messages
    messages: List[ChatMessage] = [
        TextMessage(content="Message 1", source="user"),
        TextMessage(content="Message 2", source="user"),
        TextMessage(content="Message 3", source="user"),
    ]

    # Run the team with the message list
    result = await team.run(task=messages)

    # Verify the messages were processed in order
    assert len(result.messages) == 4  # Initial messages + echo until termination
    assert result.messages[0].content == "Message 1"  # First message
    assert result.messages[1].content == "Message 2"  # Second message
    assert result.messages[2].content == "Message 3"  # Third message
    assert result.messages[3].content == "Message 1"  # Echo from first agent
    assert result.stop_reason == "Maximum number of messages 4 reached, current message count: 4"

    # Test with streaming
    await team.reset()
    index = 0
    async for message in team.run_stream(task=messages):
        if isinstance(message, TaskResult):
            assert message == result
        else:
            assert message == result.messages[index]
            index += 1

    # Test with invalid message list
    with pytest.raises(ValueError, match="All messages in task list must be valid ChatMessage types"):
        await team.run(task=["not a message"])  # type: ignore[list-item, arg-type]  # intentionally testing invalid input

    # Test with empty message list
    with pytest.raises(ValueError, match="Task list cannot be empty"):
        await team.run(task=[])


@pytest.mark.asyncio
async def test_declarative_groupchats_with_config(runtime: AgentRuntime | None) -> None:
    # Create basic agents and components for testing
    agent1 = AssistantAgent(
        "agent_1",
        model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-05-13", api_key=""),
        handoffs=["agent_2"],
    )
    agent2 = AssistantAgent("agent_2", model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-05-13", api_key=""))
    termination = MaxMessageTermination(4)
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-05-13", api_key="")

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
