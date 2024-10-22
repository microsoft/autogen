from typing import Callable, List

from ...base import BaseChatAgent, TerminationCondition
from .._events import ContentPublishEvent
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager


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

    async def select_speaker(self, thread: List[ContentPublishEvent]) -> str:
        """Select a speaker from the participants in a round-robin fashion."""
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_topic_types)
        return self._participant_topic_types[current_speaker_index]


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

            from autogen_agentchat.agents import ToolUseAssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat, StopMessageTermination

            assistant = ToolUseAssistantAgent("Assistant", model_client=..., registered_tools=...)
            team = RoundRobinGroupChat([assistant])
            await team.run("What's the weather in New York?", termination_condition=StopMessageTermination())

    A team with multiple participants:

        .. code-block:: python

            from autogen_agentchat.agents import CodingAssistantAgent, CodeExecutorAgent
            from autogen_agentchat.teams import RoundRobinGroupChat, StopMessageTermination

            coding_assistant = CodingAssistantAgent("Coding_Assistant", model_client=...)
            executor_agent = CodeExecutorAgent("Code_Executor", code_executor=...)
            team = RoundRobinGroupChat([coding_assistant, executor_agent])
            await team.run("Write a program that prints 'Hello, world!'", termination_condition=StopMessageTermination())

    """

    def __init__(self, participants: List[BaseChatAgent]):
        super().__init__(participants, group_chat_manager_class=RoundRobinGroupChatManager)

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
