from typing import List

from autogen_core.components.models import AssistantMessage, UserMessage

from ._base_group_chat_manager import BaseGroupChatManager


class RoundRobinGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker in a round-robin fashion."""

    def __init__(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
    ):
        super().__init__(
            parent_topic_type,
            group_topic_type,
            participant_topic_types,
            participant_descriptions,
        )
        self._next_speaker_index = 0

    async def select_speaker(self, thread: List[UserMessage | AssistantMessage]) -> str:
        """Select a speaker from the participants in a round-robin fashion."""
        current_speaker_index = self._next_speaker_index
        self._next_speaker_index = (current_speaker_index + 1) % len(self._participant_topic_types)
        return self._participant_topic_types[current_speaker_index]
