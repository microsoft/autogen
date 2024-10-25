import logging
from typing import Callable, List

from ... import EVENT_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from ...messages import HandoffMessage
from .._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
)
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class SwarmGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker based on handoff message only."""

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
        self._current_speaker = participant_topic_types[0]

    async def select_speaker(self, thread: List[GroupChatPublishEvent]) -> str:
        """Select a speaker from the participants based on handoff message."""
        if len(thread) > 0 and isinstance(thread[-1].agent_message, HandoffMessage):
            self._current_speaker = thread[-1].agent_message.content
            if self._current_speaker not in self._participant_topic_types:
                raise ValueError("The selected speaker in the handoff message is not a participant.")
            event_logger.debug(GroupChatSelectSpeakerEvent(selected_speaker=self._current_speaker, source=self.id))
            return self._current_speaker
        else:
            return self._current_speaker


class Swarm(BaseGroupChat):
    """(Experimental) A group chat that selects the next speaker based on handoff message only."""

    def __init__(self, participants: List[ChatAgent]):
        super().__init__(participants, group_chat_manager_class=SwarmGroupChatManager)

    def _create_group_chat_manager_factory(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None,
    ) -> Callable[[], SwarmGroupChatManager]:
        def _factory() -> SwarmGroupChatManager:
            return SwarmGroupChatManager(
                parent_topic_type,
                group_topic_type,
                participant_topic_types,
                participant_descriptions,
                termination_condition,
            )

        return _factory
