import uuid
from typing import Callable, List

from autogen_agentchat.agents._base_chat_agent import ChatMessage
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, AgentRuntime, AgentType, MessageContext, TopicId
from autogen_core.components import ClosureAgent, TypeSubscription
from autogen_core.components.tool_agent import ToolAgent
from autogen_core.components.tools import Tool

from ...agents import BaseChatAgent, TextMessage
from .._base_team import BaseTeam, TeamRunResult
from ._base_chat_agent_container import BaseChatAgentContainer
from ._events import ContentPublishEvent, ContentRequestEvent
from ._round_robin_group_chat_manager import RoundRobinGroupChatManager


class RoundRobinGroupChat(BaseTeam):
    """A team that runs a group chat with participants taking turns in a round-robin fashion.

    If a single participant is in the team, the participant will be the only speaker.

    Args:
        participants (List[BaseChatAgent]): The participants in the group chat.
        tools (List[Tool], optional): The tools to use in the group chat. Defaults to None.

    Raises:
        ValueError: If no participants are provided or if participant names are not unique.

    Examples:

    A team with one participant with tools:

        .. code-block:: python

            from autogen_agentchat.agents import ToolUseAssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat

            assistant = ToolUseAssistantAgent("Assistant", model_client=..., tool_schema=[...])
            team = RoundRobinGroupChat([assistant], tools=[...])
            await team.run("What's the weather in New York?")

    A team with multiple participants:

        .. code-block:: python

            from autogen_agentchat.agents import CodingAssistantAgent, CodeExecutorAgent
            from autogen_agentchat.teams import RoundRobinGroupChat

            coding_assistant = CodingAssistantAgent("Coding Assistant", model_client=...)
            executor_agent = CodeExecutorAgent("Code Executor", code_executor=...)
            team = RoundRobinGroupChat([coding_assistant, executor_agent])
            await team.run("Write a program that prints 'Hello, world!'")

    """

    def __init__(self, participants: List[BaseChatAgent], *, tools: List[Tool] | None = None):
        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")
        self._participants = participants
        self._team_id = str(uuid.uuid4())
        self._tools = tools or []

    def _create_factory(
        self, parent_topic_type: str, agent: BaseChatAgent, tool_agent_type: AgentType
    ) -> Callable[[], BaseChatAgentContainer]:
        def _factory() -> BaseChatAgentContainer:
            id = AgentInstantiationContext.current_agent_id()
            assert id == AgentId(type=agent.name, key=self._team_id)
            container = BaseChatAgentContainer(parent_topic_type, agent, tool_agent_type)
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

        # Register the tool agent.
        tool_agent_type = await ToolAgent.register(
            runtime, "tool_agent", lambda: ToolAgent("Tool agent for round-robin group chat", self._tools)
        )
        # No subscriptions are needed for the tool agent, which will be called via direct messages.

        # Register participants.
        participant_topic_types: List[str] = []
        participant_descriptions: List[str] = []
        for participant in self._participants:
            # Use the participant name as the agent type and topic type.
            agent_type = participant.name
            topic_type = participant.name
            # Register the participant factory.
            await BaseChatAgentContainer.register(
                runtime, type=agent_type, factory=self._create_factory(group_topic_type, participant, tool_agent_type)
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
