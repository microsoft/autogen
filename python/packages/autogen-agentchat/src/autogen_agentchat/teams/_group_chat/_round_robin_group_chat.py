import logging
from typing import Callable, List

from ... import EVENT_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from .._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
)
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class RoundRobinGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker in a round-robin fashion."""

    def __init__(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
    ) -> None:
        super().__init__(
            parent_topic_type,
            group_topic_type,
            participant_topic_types,
            participant_descriptions,
            termination_condition,
        )
        self._next_speaker_index = 0

    async def select_speaker(self, thread: List[GroupChatPublishEvent]) -> str:
        """Select a speaker from the participants in a round-robin fashion."""
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_topic_types)
        current_speaker = self._participant_topic_types[current_speaker_index]
        event_logger.debug(GroupChatSelectSpeakerEvent(selected_speaker=current_speaker, source=self.id))
        return current_speaker


class RoundRobinGroupChat(BaseGroupChat):
    """A team that runs a group chat with participants taking turns in a round-robin fashion
    to publish a message to all.

    If a single participant is in the team, the participant will be the only speaker.

    Args:
        participants (List[BaseChatAgent]): The participants in the group chat.
        tools (List[Tool], optional): The tools to use in the group chat. Defaults to None.

    Raises:
        ValueError: If no participants are provided or if participant names are not unique.

    Examples:

    A team with one participant with tools:

        .. code-block:: python

            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.task import StopMessageTermination

            model_client = OpenAIChatCompletionClient(model="gpt-4o")


            async def get_weather(location: str) -> str:
                return f"The weather in {location} is sunny."


            assistant = AssistantAgent(
                "Assistant",
                model_client=model_client,
                tools=[get_weather],
            )
            team = RoundRobinGroupChat([assistant])
            stream = team.run_stream("What's the weather in New York?", termination_condition=StopMessageTermination())
            async for message in stream:
                print(message)

    A team with multiple participants:

        .. code-block:: python

            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.task import StopMessageTermination

            model_client = OpenAIChatCompletionClient(model="gpt-4o")

            agent1 = AssistantAgent("Assistant1", model_client=model_client)
            agent2 = AssistantAgent("Assistant2", model_client=model_client)
            team = RoundRobinGroupChat([agent1, agent2])
            stream = team.run_stream("Tell me some jokes.", termination_condition=StopMessageTermination())
            async for message in stream:
                print(message)

    """

    def __init__(self, participants: List[ChatAgent], termination_condition: TerminationCondition | None = None):
        super().__init__(
            participants,
            termination_condition=termination_condition,
            group_chat_manager_class=RoundRobinGroupChatManager,
        )

    def _create_group_chat_manager_factory(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], RoundRobinGroupChatManager]:
        def _factory() -> RoundRobinGroupChatManager:
            return RoundRobinGroupChatManager(
                parent_topic_type,
                group_topic_type,
                participant_topic_types,
                participant_descriptions,
                termination_condition,
            )

        return _factory
