import asyncio
from typing import List, Sequence

import pytest
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.teams._group_chat._chat_agent_container import ChatAgentContainer
from autogen_agentchat.teams._group_chat._events import GroupChatPause, GroupChatRequestPublish, GroupChatResume
from autogen_core import AgentId, CancellationToken, SingleThreadedAgentRuntime, TopicId, TypeSubscription


class TestAgent(BaseChatAgent):
    """A test agent that does nothing."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self._is_paused = False
        self._tasks: List[asyncio.Task[None]] = []
        self.counter = 0

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return [TextMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
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


@pytest.mark.asyncio
async def test_group_chat_agent_container_pause_resume() -> None:
    runtime = SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)
    runtime.start()
    agent = TestAgent(name="test_agent", description="test agent")

    await ChatAgentContainer.register(
        runtime=runtime,
        type="test_agent",
        factory=lambda: ChatAgentContainer(
            parent_topic_type="test_parent",
            output_topic_type="test_output",
            agent=agent,
        ),
    )
    await runtime.add_subscription(TypeSubscription("test_parent", "test_agent"))

    curr_counter = agent.counter

    # Simulate a message being sent to the agent.
    await runtime.publish_message(GroupChatRequestPublish(), topic_id=TopicId(type="test_parent", source="default"))

    # Let the agent process the message.
    await asyncio.sleep(1)

    # Check that the agent's counter has increased.
    assert curr_counter < agent.counter
    curr_counter = agent.counter

    # Pause the agent.
    await runtime.send_message(GroupChatPause(), AgentId("test_agent", "default"))

    # Wait for a while for the agent to process the pause.
    await asyncio.sleep(1)

    # Get the current counter value.
    curr_counter = agent.counter

    # Wait for a while.
    await asyncio.sleep(1)

    # Check that the agent's counter has not increased.
    assert curr_counter == agent.counter

    # Resume the agent.
    await runtime.send_message(GroupChatResume(), AgentId("test_agent", "default"))

    # Wait for a while for the agent to process the resume.
    await asyncio.sleep(1)

    # Get the current counter value.
    curr_counter = agent.counter

    # Wait for a while.
    await asyncio.sleep(1)

    # Check that the agent's counter has increased.
    assert curr_counter < agent.counter

    # Clean up
    await runtime.stop()
    await agent.close()
