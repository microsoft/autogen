import asyncio
from typing import AsyncGenerator, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import AgentRuntime, CancellationToken, SingleThreadedAgentRuntime


class _EchoAgent(BaseChatAgent):
    """A simple echo agent for testing."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        if len(messages) > 0:
            assert isinstance(messages[0], TextMessage)
            return Response(chat_message=TextMessage(content=messages[0].content, source=self.name))
        return Response(chat_message=TextMessage(content="echo", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


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
async def test_get_thread_after_run(runtime: AgentRuntime | None) -> None:
    """Test that get_thread returns the message thread after a run."""
    agent1 = _EchoAgent("agent1", "echo agent 1")
    agent2 = _EchoAgent("agent2", "echo agent 2")
    termination = MaxMessageTermination(3)
    team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination, runtime=runtime)

    result = await team.run(task="Hello")

    # Get the thread after the run.
    thread = await team.get_thread()

    # The thread should contain the task message plus agent responses.
    assert len(thread) > 0
    # The first message should be the task.
    assert isinstance(thread[0], TextMessage)
    assert thread[0].content == "Hello"
    # The thread length should match the result messages (minus the stop message if any).
    chat_messages = [m for m in result.messages if not isinstance(m, type(None))]
    assert len(thread) == len(chat_messages)


@pytest.mark.asyncio
async def test_get_thread_empty_after_reset(runtime: AgentRuntime | None) -> None:
    """Test that get_thread returns an empty list after reset."""
    agent1 = _EchoAgent("agent1", "echo agent 1")
    termination = MaxMessageTermination(2)
    team = RoundRobinGroupChat([agent1], termination_condition=termination, runtime=runtime)

    await team.run(task="Hello")

    # Thread should have messages.
    thread = await team.get_thread()
    assert len(thread) > 0

    # Reset the team.
    await team.reset()

    # Thread should now be empty.
    thread = await team.get_thread()
    assert len(thread) == 0


@pytest.mark.asyncio
async def test_get_thread_not_initialized(runtime: AgentRuntime | None) -> None:
    """Test that get_thread raises an error if the team has not been initialized."""
    agent1 = _EchoAgent("agent1", "echo agent 1")
    team = RoundRobinGroupChat([agent1], runtime=runtime)

    with pytest.raises(RuntimeError, match="not been initialized"):
        await team.get_thread()
