import asyncio
import json
import logging
from typing import AsyncGenerator, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    BaseChatAgent,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    TextMessage,
)
from autogen_agentchat.teams import (
    MagenticOneGroupChat,
)
from autogen_agentchat.teams._group_chat._magentic_one._magentic_one_orchestrator import MagenticOneOrchestrator
from autogen_core import AgentId, AgentRuntime, CancellationToken, SingleThreadedAgentRuntime
from autogen_ext.models.replay import ReplayChatCompletionClient
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_magentic_one_group_chat.log"))


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
async def test_magentic_one_group_chat_cancellation(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=["test", "test", json.dumps({"is_request_satisfied": {"answer": True, "reason": "test"}})],
    )

    # Set max_turns to a large number to avoid stopping due to max_turns before cancellation.
    team = MagenticOneGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client, runtime=runtime
    )
    cancellation_token = CancellationToken()
    run_task = asyncio.create_task(
        team.run(
            task="Write a program that prints 'Hello, world!'",
            cancellation_token=cancellation_token,
        )
    )

    # Cancel the task.
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task


@pytest.mark.asyncio
async def test_magentic_one_group_chat_basic(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "No facts",
            "No plan",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Continue task", "reason": "test"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            json.dumps(
                {
                    "is_request_satisfied": {"answer": True, "reason": "Because"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Task completed", "reason": "Because"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            "print('Hello, world!')",
        ],
    )

    team = MagenticOneGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client, runtime=runtime
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 5
    assert result.messages[2].to_text() == "Continue task"
    assert result.messages[4].to_text() == "print('Hello, world!')"
    assert result.stop_reason is not None and result.stop_reason == "Because"

    # Test save and load.
    state = await team.save_state()
    team2 = MagenticOneGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client, runtime=runtime
    )
    await team2.load_state(state)
    state2 = await team2.save_state()
    assert state == state2
    manager_1 = await team._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team._group_chat_manager_name}_{team._team_id}", team._team_id),  # pyright: ignore
        MagenticOneOrchestrator,  # pyright: ignore
    )  # pyright: ignore
    manager_2 = await team2._runtime.try_get_underlying_agent_instance(  # pyright: ignore
        AgentId(f"{team2._group_chat_manager_name}_{team2._team_id}", team2._team_id),  # pyright: ignore
        MagenticOneOrchestrator,  # pyright: ignore
    )  # pyright: ignore
    assert manager_1._message_thread == manager_2._message_thread  # pyright: ignore
    assert manager_1._task == manager_2._task  # pyright: ignore
    assert manager_1._facts == manager_2._facts  # pyright: ignore
    assert manager_1._plan == manager_2._plan  # pyright: ignore
    assert manager_1._n_rounds == manager_2._n_rounds  # pyright: ignore
    assert manager_1._n_stalls == manager_2._n_stalls  # pyright: ignore


@pytest.mark.asyncio
async def test_magentic_one_group_chat_with_stalls(runtime: AgentRuntime | None) -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "No facts",
            "No plan",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": False, "reason": "test"},
                    "is_in_loop": {"answer": True, "reason": "test"},
                    "instruction_or_question": {"answer": "Stalling", "reason": "test"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": False, "reason": "test"},
                    "is_in_loop": {"answer": True, "reason": "test"},
                    "instruction_or_question": {"answer": "Stalling again", "reason": "test"},
                    "next_speaker": {"answer": "agent_2", "reason": "test"},
                }
            ),
            "No facts2",
            "No plan2",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": True, "reason": "test"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Task completed", "reason": "test"},
                    "next_speaker": {"answer": "agent_3", "reason": "test"},
                }
            ),
            "print('Hello, world!')",
        ],
    )

    team = MagenticOneGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4],
        model_client=model_client,
        max_stalls=2,
        runtime=runtime,
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 6
    assert isinstance(result.messages[1], TextMessage)
    assert result.messages[1].content.startswith("\nWe are working to address the following user request:")
    assert isinstance(result.messages[4], TextMessage)
    assert result.messages[4].content.startswith("\nWe are working to address the following user request:")
    assert result.stop_reason is not None and result.stop_reason == "test"
