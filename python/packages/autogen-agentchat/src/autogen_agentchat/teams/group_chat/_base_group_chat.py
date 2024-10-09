import uuid
from abc import ABC, abstractmethod
from typing import Callable, List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, AgentRuntime, AgentType, MessageContext, TopicId
from autogen_core.components import ClosureAgent, TypeSubscription
from autogen_core.components.tool_agent import ToolAgent
from autogen_core.components.tools import Tool

from autogen_agentchat.agents._base_chat_agent import ChatMessage

from ...agents import BaseChatAgent, BaseToolUseChatAgent, TextMessage
from .._base_team import BaseTeam, TeamRunResult
from .._events import ContentPublishEvent, ContentRequestEvent
from ._base_chat_agent_container import BaseChatAgentContainer
from ._base_group_chat_manager import BaseGroupChatManager


class BaseGroupChat(BaseTeam, ABC):
    """The base class for group chat teams.

    To implement a group chat team, first create a subclass of :class:`BaseGroupChatManager` and then
    create a subclass of :class:`BaseGroupChat` that uses the group chat manager.
    """

    def __init__(self, participants: List[BaseChatAgent], group_chat_manager_class: type[BaseGroupChatManager]):
        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")
        for participant in participants:
            if isinstance(participant, BaseToolUseChatAgent) and not participant.registered_tools:
                raise ValueError(
                    f"Participant '{participant.name}' is a tool use agent so it must have registered tools."
                )
        self._participants = participants
        self._team_id = str(uuid.uuid4())
        self._base_group_chat_manager_class = group_chat_manager_class

    @abstractmethod
    def _create_group_chat_manager_factory(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
    ) -> Callable[[], BaseGroupChatManager]: ...

    def _create_participant_factory(
        self, parent_topic_type: str, agent: BaseChatAgent, tool_agent_type: AgentType | None
    ) -> Callable[[], BaseChatAgentContainer]:
        def _factory() -> BaseChatAgentContainer:
            id = AgentInstantiationContext.current_agent_id()
            assert id == AgentId(type=agent.name, key=self._team_id)
            container = BaseChatAgentContainer(parent_topic_type, agent, tool_agent_type)
            assert container.id == id
            return container

        return _factory

    def _create_tool_agent_factory(
        self,
        caller_name: str,
        tools: List[Tool],
    ) -> Callable[[], ToolAgent]:
        def _factory() -> ToolAgent:
            return ToolAgent(f"Tool agent for {caller_name}", tools)

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
            if isinstance(participant, BaseToolUseChatAgent):
                assert participant.registered_tools is not None and len(participant.registered_tools) > 0
                # Register the tool agent.
                tool_agent_type = await ToolAgent.register(
                    runtime,
                    f"tool_agent_for_{participant.name}",
                    self._create_tool_agent_factory(participant.name, participant.registered_tools),
                )
                # No subscriptions are needed for the tool agent, which will be called via direct messages.
            else:
                # No tool agent is needed.
                tool_agent_type = None

            # Use the participant name as the agent type and topic type.
            agent_type = participant.name
            topic_type = participant.name
            # Register the participant factory.
            await BaseChatAgentContainer.register(
                runtime,
                type=agent_type,
                factory=self._create_participant_factory(group_topic_type, participant, tool_agent_type),
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

        group_chat_messages: List[ChatMessage] = []

        async def collect_group_chat_messages(
            _runtime: AgentRuntime, id: AgentId, message: ContentPublishEvent, ctx: MessageContext
        ) -> None:
            group_chat_messages.append(message.agent_message)

        await ClosureAgent.register(
            runtime,
            type="collect_group_chat_messages",
            closure=collect_group_chat_messages,
            subscriptions=lambda: [
                TypeSubscription(topic_type=group_topic_type, agent_type="collect_group_chat_messages")
            ],
        )

        # Start the runtime.
        runtime.start()

        # Run the team by publishing the task to the team topic and then requesting the result.
        team_topic_id = TopicId(type=team_topic_type, source=self._team_id)
        group_chat_manager_topic_id = TopicId(type=group_chat_manager_topic_type, source=self._team_id)
        await runtime.publish_message(
            ContentPublishEvent(agent_message=TextMessage(content=task, source="user")),
            topic_id=team_topic_id,
        )
        await runtime.publish_message(ContentRequestEvent(), topic_id=group_chat_manager_topic_id)

        # Wait for the runtime to stop.
        await runtime.stop_when_idle()

        return TeamRunResult(messages=group_chat_messages)
