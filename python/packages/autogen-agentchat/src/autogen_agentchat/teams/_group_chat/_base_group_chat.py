import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import (
    AgentId,
    AgentInstantiationContext,
    AgentRuntime,
    AgentType,
    CancellationToken,
    MessageContext,
    TopicId,
)
from autogen_core.components import ClosureAgent, TypeSubscription

from ... import EVENT_LOGGER_NAME
from ...base import ChatAgent, TaskResult, Team, TerminationCondition
from ...messages import AgentMessage, TextMessage
from ._base_group_chat_manager import BaseGroupChatManager
from ._chat_agent_container import ChatAgentContainer
from ._events import GroupChatMessage, GroupChatStart, GroupChatTermination

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class BaseGroupChat(Team, ABC):
    """The base class for group chat teams.

    To implement a group chat team, first create a subclass of :class:`BaseGroupChatManager` and then
    create a subclass of :class:`BaseGroupChat` that uses the group chat manager.
    """

    def __init__(
        self,
        participants: List[ChatAgent],
        group_chat_manager_class: type[BaseGroupChatManager],
        termination_condition: TerminationCondition | None = None,
    ):
        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")
        self._participants = participants
        self._team_id = str(uuid.uuid4())
        self._base_group_chat_manager_class = group_chat_manager_class
        self._termination_condition = termination_condition
        self._message_thread: List[AgentMessage] = []

    @abstractmethod
    def _create_group_chat_manager_factory(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        message_thread: List[AgentMessage],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], BaseGroupChatManager]: ...

    def _create_participant_factory(
        self,
        parent_topic_type: str,
        output_topic_type: str,
        agent: ChatAgent,
    ) -> Callable[[], ChatAgentContainer]:
        def _factory() -> ChatAgentContainer:
            id = AgentInstantiationContext.current_agent_id()
            assert id == AgentId(type=agent.name, key=self._team_id)
            container = ChatAgentContainer(parent_topic_type, output_topic_type, agent)
            assert container.id == id
            return container

        return _factory

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the team and return the result. The base implementation uses
        :meth:`run_stream` to run the team and then returns the final result."""
        async for message in self.run_stream(
            task,
            cancellation_token=cancellation_token,
        ):
            if isinstance(message, TaskResult):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def run_stream(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[AgentMessage | TaskResult, None]:
        """Run the team and produces a stream of messages and the final result
        of the type :class:`TaskResult` as the last item in the stream."""

        # TODO: runtime is currently a local variable, but it should be stored in
        # a managed context so it can be accessed by all nested teams. Also, the runtime
        # should be not be started or stopped by the team, but by the context.

        # Create the runtime.
        runtime = SingleThreadedAgentRuntime()

        # Constants for the group chat manager.
        group_chat_manager_agent_type = AgentType("group_chat_manager")
        group_chat_manager_topic_type = group_chat_manager_agent_type.type
        group_topic_type = "round_robin_group_topic"
        output_topic_type = "output_topic"

        # Register participants.
        participant_topic_types: List[str] = []
        participant_descriptions: List[str] = []
        for participant in self._participants:
            # Use the participant name as the agent type and topic type.
            agent_type = participant.name
            topic_type = participant.name
            # Register the participant factory.
            await ChatAgentContainer.register(
                runtime,
                type=agent_type,
                factory=self._create_participant_factory(group_topic_type, output_topic_type, participant),
            )
            # Add subscriptions for the participant.
            await runtime.add_subscription(TypeSubscription(topic_type=topic_type, agent_type=agent_type))
            await runtime.add_subscription(TypeSubscription(topic_type=group_topic_type, agent_type=agent_type))
            # Add the participant to the lists.
            participant_descriptions.append(participant.description)
            participant_topic_types.append(topic_type)

        # Register the group chat manager.
        await self._base_group_chat_manager_class.register(
            runtime,
            type=group_chat_manager_agent_type.type,
            factory=self._create_group_chat_manager_factory(
                group_topic_type=group_topic_type,
                output_topic_type=output_topic_type,
                participant_topic_types=participant_topic_types,
                participant_descriptions=participant_descriptions,
                message_thread=self._message_thread,
                termination_condition=self._termination_condition,
            ),
        )
        # Add subscriptions for the group chat manager.
        await runtime.add_subscription(
            TypeSubscription(topic_type=group_chat_manager_topic_type, agent_type=group_chat_manager_agent_type.type)
        )
        await runtime.add_subscription(
            TypeSubscription(topic_type=group_topic_type, agent_type=group_chat_manager_agent_type.type)
        )

        # Create a closure agent to collect the output messages.
        stop_reason: str | None = None
        output_message_queue: asyncio.Queue[AgentMessage | None] = asyncio.Queue()

        async def collect_output_messages(
            _runtime: AgentRuntime,
            id: AgentId,
            message: GroupChatStart | GroupChatMessage | GroupChatTermination,
            ctx: MessageContext,
        ) -> None:
            event_logger.info(message.message)
            if isinstance(message, GroupChatTermination):
                nonlocal stop_reason
                stop_reason = message.message.content
                return
            await output_message_queue.put(message.message)

        await ClosureAgent.register(
            runtime,
            type="collect_output_messages",
            closure=collect_output_messages,
            subscriptions=lambda: [
                TypeSubscription(topic_type=output_topic_type, agent_type="collect_output_messages"),
            ],
        )

        # Start the runtime.
        runtime.start()

        # Run the team by publishing the task to the group chat manager.
        first_chat_message = TextMessage(content=task, source="user")
        await runtime.publish_message(
            GroupChatStart(message=first_chat_message),
            topic_id=TopicId(type=group_topic_type, source=self._team_id),
        )

        # Start a coroutine to stop the runtime and signal the output message queue is complete.
        async def stop_runtime() -> None:
            await runtime.stop_when_idle()
            await output_message_queue.put(None)

        shutdown_task = asyncio.create_task(stop_runtime())

        # Collect the output messages in order.
        output_messages: List[AgentMessage] = []
        # Yield the messsages until the queue is empty.
        while True:
            message = await output_message_queue.get()
            if message is None:
                break
            yield message
            output_messages.append(message)

        # Wait for the shutdown task to finish.
        await shutdown_task

        # Yield the final result.
        yield TaskResult(messages=output_messages, stop_reason=stop_reason)
