import asyncio
from typing import Sequence

import pytest
from autogen_agentchat.agents import AssistantAgent, BaseChatAgent
from autogen_agentchat.base import Response, TerminationCondition
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_core import CancellationToken, SingleThreadedAgentRuntime


class _EchoAgent(BaseChatAgent):
    """A simple agent that echoes back a fixed response."""

    def __init__(self, name: str, response: str = "hello") -> None:
        super().__init__(name=name, description="A test echo agent.")
        self._response = response
        self.call_count = 0

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return [TextMessage]

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        self.call_count += 1
        return Response(
            chat_message=TextMessage(content=self._response, source=self.name),
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.call_count = 0


@pytest.mark.asyncio
async def test_get_thread_after_run() -> None:
    """After a run completes, get_thread returns the same messages as TaskResult."""
    agent1 = _EchoAgent("agent1", "alpha")
    agent2 = _EchoAgent("agent2", "beta")
    termination = MaxMessageTermination(4)
    team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
    )

    result = await team.run(task="start")

    thread = await team.get_thread()

    # The thread should be non-empty.
    assert len(thread) > 0

    # The thread content should match the TaskResult messages.
    assert len(thread) == len(result.messages)
    for t_msg, r_msg in zip(thread, result.messages, strict=True):
        assert t_msg.content == r_msg.content  # type: ignore[attr-defined]
        assert t_msg.source == r_msg.source  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_thread_not_initialized_raises() -> None:
    """get_thread before the first run raises RuntimeError."""
    agent = _EchoAgent("agent1")
    team = RoundRobinGroupChat(
        participants=[agent],
        termination_condition=MaxMessageTermination(2),
    )

    with pytest.raises(RuntimeError, match="not been initialized"):
        await team.get_thread()


@pytest.mark.asyncio
async def test_get_thread_returns_snapshot() -> None:
    """Mutating the returned list does not affect the manager's internal state."""
    agent1 = _EchoAgent("agent1", "ping")
    agent2 = _EchoAgent("agent2", "pong")
    termination = MaxMessageTermination(4)
    team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
    )

    await team.run(task="go")

    thread = await team.get_thread()
    original_len = len(thread)

    # Mutate the returned list.
    thread.clear()
    assert len(thread) == 0

    # The manager's thread should be unaffected.
    thread2 = await team.get_thread()
    assert len(thread2) == original_len


@pytest.mark.asyncio
async def test_get_thread_with_no_task() -> None:
    """get_thread works after a run_stream without an initial task (continuation)."""
    agent = _EchoAgent("agent1", "reply")
    termination = MaxMessageTermination(2)
    team = RoundRobinGroupChat(
        participants=[agent],
        termination_condition=termination,
    )

    # First run with a task.
    await team.run(task="hello")

    # get_thread should work after run.
    thread = await team.get_thread()
    assert len(thread) > 0
