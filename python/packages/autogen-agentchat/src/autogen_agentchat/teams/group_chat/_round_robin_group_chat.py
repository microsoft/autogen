import asyncio
import uuid
from typing import Callable, List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, AgentRuntime, AgentType, MessageContext, TopicId
from autogen_core.components import ClosureAgent, TypeSubscription
from autogen_core.components.models import UserMessage

from ...agents import BaseChatAgent
from .._base_team import BaseTeam, TeamRunResult
from ._base_chat_agent_container import BaseChatAgentContainer
from ._messages import ContentPublishEvent, ContentRequestEvent
from ._round_robin_group_chat_manager import RoundRobinGroupChatManager


class RoundRobinGroupChat(BaseTeam):
    def __init__(self, participants: List[BaseChatAgent]):
        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")
        self._participants = participants
        self._team_id = str(uuid.uuid4())

    def _create_factory(self, parent_topic_type: str, agent: BaseChatAgent) -> Callable[[], BaseChatAgentContainer]:
        def _factory() -> BaseChatAgentContainer:
            id = AgentInstantiationContext.current_agent_id()
            assert id == AgentId(type=agent.name, key=self._team_id)
            container = BaseChatAgentContainer(parent_topic_type, agent)
            assert container.id == id
            return container

        return _factory

    async def run(self, task: str) -> TeamRunResult:
        """Run the team and return the result."""
        # Create the runtime.
        runtime = SingleThreadedAgentRuntime()

        # Constants for the group chat manager.
        group_chat_manager_agent_type = AgentType("group_chat_manager")
        group_chat_manager_topic_type = group_chat_manager_agent_type.type
        group_topic_type = "round_robin_group_topic"
        team_topic_type = "team_topic"

        # Register participants.
        participant_topic_types: List[str] = []
        participant_descriptions: List[str] = []
        for participant in self._participants:
            # Use the participant name as the agent type and topic type.
            agent_type = participant.name
            topic_type = participant.name
            # Register the participant factory.
            await BaseChatAgentContainer.register(
                runtime, type=agent_type, factory=self._create_factory(group_topic_type, participant)
            )
            # Add subscriptions for the participant.
            await runtime.add_subscription(TypeSubscription(topic_type=topic_type, agent_type=agent_type))
            await runtime.add_subscription(TypeSubscription(topic_type=group_topic_type, agent_type=agent_type))
            # Add the participant to the lists.
            participant_descriptions.append(participant.description)
            participant_topic_types.append(topic_type)

        # Register the group chat manager.
        await RoundRobinGroupChatManager.register(
            runtime,
            type=group_chat_manager_agent_type.type,
            factory=lambda: RoundRobinGroupChatManager(
                parent_topic_type=team_topic_type,
                group_topic_type=group_topic_type,
                participant_topic_types=participant_topic_types,
                participant_descriptions=participant_descriptions,
            ),
        )
        # Add subscriptions for the group chat manager.
        await runtime.add_subscription(
            TypeSubscription(topic_type=group_chat_manager_topic_type, agent_type=group_chat_manager_agent_type.type)
        )
        await runtime.add_subscription(
            TypeSubscription(topic_type=group_topic_type, agent_type=group_chat_manager_agent_type.type)
        )
        await runtime.add_subscription(
            TypeSubscription(topic_type=team_topic_type, agent_type=group_chat_manager_agent_type.type)
        )

        # Create a closure agent to recieve the final result.
        team_messages = asyncio.Queue[ContentPublishEvent]()

        async def output_result(
            _runtime: AgentRuntime, id: AgentId, message: ContentPublishEvent, ctx: MessageContext
        ) -> None:
            await team_messages.put(message)

        await ClosureAgent.register(
            runtime,
            type="output_result",
            closure=output_result,
            subscriptions=lambda: [TypeSubscription(topic_type=team_topic_type, agent_type="output_result")],
        )

        # Start the runtime.
        runtime.start()

        # Run the team by publishing the task to the team topic and then requesting the result.
        team_topic_id = TopicId(type=team_topic_type, source=self._team_id)
        group_chat_manager_topic_id = TopicId(type=group_chat_manager_topic_type, source=self._team_id)
        await runtime.publish_message(
            ContentPublishEvent(content=UserMessage(content=task, source="user"), request_pause=False),
            topic_id=team_topic_id,
        )
        await runtime.publish_message(ContentRequestEvent(), topic_id=group_chat_manager_topic_id)

        # Wait for the runtime to stop.
        await runtime.stop_when_idle()

        # Get the last message from the team.
        last_message = None
        while not team_messages.empty():
            last_message = await team_messages.get()

        assert (
            last_message is not None
            and isinstance(last_message.content, UserMessage)
            and isinstance(last_message.content.content, str)
        )
        return TeamRunResult(last_message.content.content)
