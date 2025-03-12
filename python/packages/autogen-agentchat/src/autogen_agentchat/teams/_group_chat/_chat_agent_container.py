from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator, List, Mapping

from autogen_core import AgentId, AgentRuntime, DefaultTopicId, MessageContext, TopicId, event, rpc

from ...base import ChatAgent, Response
from ...messages import ChatMessage
from ...state import ChatAgentContainerState
from ._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatPause,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatResume,
    GroupChatStart,
)
from ._sequential_routed_agent import SequentialRoutedAgent


class TeamRuntimeContext:
    """A static class that provides context for agent instantiation.

    This static class can be used to access the current runtime and agent ID
    during agent instantiation -- inside the factory function or the agent's
    class constructor.

    Example:

        Get the current runtime and agent ID inside the factory function and
        the agent's constructor:

        .. code-block:: python

            import asyncio
            from dataclasses import dataclass

            from autogen_core import (
                AgentId,
                AgentInstantiationContext,
                MessageContext,
                RoutedAgent,
                SingleThreadedAgentRuntime,
                message_handler,
            )


            @dataclass
            class TestMessage:
                content: str


            class TestAgent(RoutedAgent):
                def __init__(self, description: str):
                    super().__init__(description)
                    # Get the current runtime -- we don't use it here, but it's available.
                    _ = AgentInstantiationContext.current_runtime()
                    # Get the current agent ID.
                    agent_id = AgentInstantiationContext.current_agent_id()
                    print(f"Current AgentID from constructor: {agent_id}")

                @message_handler
                async def handle_test_message(self, message: TestMessage, ctx: MessageContext) -> None:
                    print(f"Received message: {message.content}")


            def test_agent_factory() -> TestAgent:
                # Get the current runtime -- we don't use it here, but it's available.
                _ = AgentInstantiationContext.current_runtime()
                # Get the current agent ID.
                agent_id = AgentInstantiationContext.current_agent_id()
                print(f"Current AgentID from factory: {agent_id}")
                return TestAgent(description="Test agent")


            async def main() -> None:
                # Create a SingleThreadedAgentRuntime instance.
                runtime = SingleThreadedAgentRuntime()

                # Start the runtime.
                runtime.start()

                # Register the agent type with a factory function.
                await runtime.register_factory("test_agent", test_agent_factory)

                # Send a message to the agent. The runtime will instantiate the agent and call the message handler.
                await runtime.send_message(TestMessage(content="Hello, world!"), AgentId("test_agent", "default"))

                # Stop the runtime.
                await runtime.stop()


            asyncio.run(main())

    """

    def __init__(self) -> None:
        raise RuntimeError(
            "TeamRuntimeContext cannot be instantiated. It is a static class that provides context management for agent instantiation."
        )

    _TEAM_RUNTIME_CONTEXT_VAR: ClassVar[ContextVar[tuple[AgentRuntime, TopicId]]] = ContextVar(
        "_TEAM_RUNTIME_CONTEXT_VAR"
    )

    @classmethod
    @contextmanager
    def populate_context(cls, ctx: tuple[AgentRuntime, TopicId]) -> Generator[None, Any, None]:
        """:meta private:"""
        token = TeamRuntimeContext._TEAM_RUNTIME_CONTEXT_VAR.set(ctx)
        try:
            yield
        finally:
            TeamRuntimeContext._TEAM_RUNTIME_CONTEXT_VAR.reset(token)

    @classmethod
    def current_runtime(cls) -> AgentRuntime:
        try:
            return cls._TEAM_RUNTIME_CONTEXT_VAR.get()[0]
        except LookupError as e:
            raise RuntimeError(
                "TeamRuntimeContext.runtime() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e

    @classmethod
    def output_channel(cls) -> TopicId:
        try:
            return cls._TEAM_RUNTIME_CONTEXT_VAR.get()[1]
        except LookupError as e:
            raise RuntimeError(
                "TeamRuntimeContext.agent_id() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e


class ChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.base.ChatAgent` so that it can be used in a
    group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        output_topic_type (str): The topic type for the output.
        agent (ChatAgent): The agent to delegate message handling to.
    """

    def __init__(self, parent_topic_type: str, output_topic_type: str, agent: ChatAgent) -> None:
        super().__init__(
            description=agent.description,
            sequential_message_types=[
                GroupChatStart,
                GroupChatRequestPublish,
                GroupChatReset,
                GroupChatAgentResponse,
            ],
        )
        self._parent_topic_type = parent_topic_type
        self._output_topic_type = output_topic_type
        self._agent = agent
        self._message_buffer: List[ChatMessage] = []

    @event
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle a start event by appending the content to the buffer."""
        if message.messages is not None:
            self._message_buffer.extend(message.messages)

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        """Handle an agent response event by appending the content to the buffer."""
        self._message_buffer.append(message.agent_response.chat_message)

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        """Handle a reset event by resetting the agent."""
        self._message_buffer.clear()
        await self._agent.on_reset(ctx.cancellation_token)

    @event
    async def handle_request(self, message: GroupChatRequestPublish, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        with TeamRuntimeContext.populate_context((self._runtime, DefaultTopicId(type=self._output_topic_type))):
            # Pass the messages in the buffer to the delegate agent.
            response: Response | None = None
            async for msg in self._agent.on_messages_stream(self._message_buffer, ctx.cancellation_token):
                if isinstance(msg, Response):
                    # Log the response.
                    await self.publish_message(
                        GroupChatMessage(message=msg.chat_message),
                        topic_id=DefaultTopicId(type=self._output_topic_type),
                    )
                    response = msg
                else:
                    # Log the message.
                    await self.publish_message(
                        GroupChatMessage(message=msg), topic_id=DefaultTopicId(type=self._output_topic_type)
                    )
            if response is None:
                raise ValueError(
                    "The agent did not produce a final response. Check the agent's on_messages_stream method."
                )

        # Publish the response to the group chat.
        self._message_buffer.clear()
        await self.publish_message(
            GroupChatAgentResponse(agent_response=response),
            topic_id=DefaultTopicId(type=self._parent_topic_type),
            cancellation_token=ctx.cancellation_token,
        )

    @rpc
    async def handle_pause(self, message: GroupChatPause, ctx: MessageContext) -> None:
        """Handle a pause event by pausing the agent."""
        await self._agent.on_pause(ctx.cancellation_token)

    @rpc
    async def handle_resume(self, message: GroupChatResume, ctx: MessageContext) -> None:
        """Handle a resume event by resuming the agent."""
        await self._agent.on_resume(ctx.cancellation_token)

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in agent container: {type(message)}")

    async def save_state(self) -> Mapping[str, Any]:
        agent_state = await self._agent.save_state()
        state = ChatAgentContainerState(agent_state=agent_state, message_buffer=list(self._message_buffer))
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        container_state = ChatAgentContainerState.model_validate(state)
        self._message_buffer = list(container_state.message_buffer)
        await self._agent.load_state(container_state.agent_state)
