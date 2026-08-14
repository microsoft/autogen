import asyncio
from typing import AsyncGenerator, List, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import AgentRuntime, CancellationToken, SingleThreadedAgentRuntime


class TestAgent(BaseChatAgent):
    """A test agent that does nothing."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self._is_paused = False
        self._tasks: List[asyncio.Task[None]] = []
        self.counter = 0

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return [TextMessage]

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        assert not self._is_paused, "Agent is paused"

        async def _process() -> None:
            # Simulate a repetitive task that runs forever.
            while True:
                if self._is_paused:
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # Simulate a I/O operation that takes time, e.g., a browser operation.
                    await asyncio.sleep(0.1)
                    self.counter += 1

        curr_task = asyncio.create_task(_process())
        self._tasks.append(curr_task)

        try:
            # This will never return until the task is cancelled, at which point it will
            # raise an exception.
            await curr_task
        except asyncio.CancelledError:
            # The task was cancelled, so we can safely ignore this.
            pass

        return Response(
            chat_message=TextMessage(
                source=self.name,
                content="",
            ),
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.counter = 0

    async def on_pause(self, cancellation_token: CancellationToken) -> None:
        self._is_paused = True

    async def on_resume(self, cancellation_token: CancellationToken) -> None:
        self._is_paused = False

    async def close(self) -> None:
        # Cancel all tasks and wait for them to finish.
        while self._tasks:
            task = self._tasks.pop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
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
async def test_group_chat_pause_resume(runtime: AgentRuntime | None) -> None:
    agent = TestAgent(name="test_agent", description="test agent")

    team = RoundRobinGroupChat([agent], runtime=runtime, max_turns=1)

    # Run the team in a separate task.
    team_task = asyncio.create_task(team.run())

    # Get the current counter.
    curr_counter = agent.counter

    # Let the agent process the counter for a while.
    await asyncio.sleep(1)

    # Check that the agent's counter has increased.
    assert curr_counter < agent.counter
    curr_counter = agent.counter

    # Pause the team.
    await team.pause()

    # Wait for a while for the agent to process the pause.
    await asyncio.sleep(1)

    # Get the current counter value.
    curr_counter = agent.counter

    # Wait for a while.
    await asyncio.sleep(1)

    # Check that the agent's counter has not increased.
    assert curr_counter == agent.counter

    # Resume the agent.
    await team.resume()

    # Wait for a while for the agent to process the resume.
    await asyncio.sleep(1)

    # Get the current counter value.
    curr_counter = agent.counter

    # Wait for a while.
    await asyncio.sleep(1)

    # Check that the agent's counter has increased.
    assert curr_counter < agent.counter

    # Clean up -- force the agent to respond and terminate the team.
    await agent.close()

    # Wait for the team to terminate.
    await team_task
