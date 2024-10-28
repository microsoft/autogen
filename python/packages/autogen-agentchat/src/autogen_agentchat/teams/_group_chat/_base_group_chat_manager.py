import logging
from abc import ABC, abstractmethod
from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ... import EVENT_LOGGER_NAME
from ...base import TerminationCondition
from .._events import (
    GroupChatPublishEvent,
    GroupChatRequestPublishEvent,
    TerminationEvent,
)
from ._sequential_routed_agent import SequentialRoutedAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class BaseGroupChatManager(SequentialRoutedAgent, ABC):
    """Base class for a group chat manager that manages a group chat with multiple participants.

    It is the responsibility of the caller to ensure:
    - All participants must subscribe to the group chat topic and each of their own topics.
    - The group chat manager must subscribe to the parent topic and the group chat topic.
    - The agent types of the participants must be unique.
    - For each participant, the agent type must be the same as the topic type.

    Without the above conditions, the group chat will not function correctly.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        group_topic_type (str): The topic type of the group chat.
        participant_topic_types (List[str]): The topic types of the participants.
        participant_descriptions (List[str]): The descriptions of the participants
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.

    Raises:
        ValueError: If the number of participant topic types, agent types, and descriptions are not the same.
        ValueError: If the participant topic types are not unique.
        ValueError: If the group topic type is in the participant topic types.
        ValueError: If the parent topic type is in the participant topic types.
        ValueError: If the group topic type is the same as the parent topic type.
    """

    def __init__(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None = None,
    ):
        super().__init__(description="Group chat manager")
        self._parent_topic_type = parent_topic_type
        self._group_topic_type = group_topic_type
        if len(participant_topic_types) != len(participant_descriptions):
            raise ValueError("The number of participant topic types, agent types, and descriptions must be the same.")
        if len(set(participant_topic_types)) != len(participant_topic_types):
            raise ValueError("The participant topic types must be unique.")
        if group_topic_type in participant_topic_types:
            raise ValueError("The group topic type must not be in the participant topic types.")
        if parent_topic_type in participant_topic_types:
            raise ValueError("The parent topic type must not be in the participant topic types.")
        if group_topic_type == parent_topic_type:
            raise ValueError("The group topic type must not be the same as the parent topic type.")
        self._participant_topic_types = participant_topic_types
        self._participant_descriptions = participant_descriptions
        self._message_thread: List[GroupChatPublishEvent] = []
        self._termination_condition = termination_condition

    @event
    async def handle_content_publish(self, message: GroupChatPublishEvent, ctx: MessageContext) -> None:
        """Handle a content publish event.

        If the event is from the parent topic, add the message to the thread.

        If the event is from the group chat topic, add the message to the thread and select a speaker to continue the conversation.
        If the event from the group chat session requests a pause, publish the last message to the parent topic."""
        assert ctx.topic_id is not None

        event_logger.info(message)

        if self._termination_condition is not None and self._termination_condition.terminated:
            # The group chat has been terminated.
            return

        # Process event from parent.
        if ctx.topic_id.type == self._parent_topic_type:
            self._message_thread.append(message)
            await self.publish_message(
                GroupChatPublishEvent(agent_message=message.agent_message, source=self.id),
                topic_id=DefaultTopicId(type=self._group_topic_type),
            )
            if self._termination_condition is not None:
                stop_message = await self._termination_condition([message.agent_message])
                if stop_message is not None:
                    event_logger.info(TerminationEvent(agent_message=stop_message, source=self.id))
                    # Stop the group chat.
            return

        # Process event from the group chat this agent manages.
        assert ctx.topic_id.type == self._group_topic_type
        self._message_thread.append(message)

        # Check if the conversation should be terminated.
        if self._termination_condition is not None:
            stop_message = await self._termination_condition([message.agent_message])
            if stop_message is not None:
                event_logger.info(TerminationEvent(agent_message=stop_message, source=self.id))
                # Stop the group chat.
                # TODO: this should be different if the group chat is nested.
                return

        # Select a speaker to continue the conversation.
        speaker_topic_type = await self.select_speaker(self._message_thread)

        await self.publish_message(GroupChatRequestPublishEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @event
    async def handle_content_request(self, message: GroupChatRequestPublishEvent, ctx: MessageContext) -> None:
        """Handle a content request by selecting a speaker to start the conversation."""
        assert ctx.topic_id is not None
        if ctx.topic_id.type == self._group_topic_type:
            raise RuntimeError("Content request event from the group chat topic is not allowed.")

        if self._termination_condition is not None and self._termination_condition.terminated:
            # The group chat has been terminated.
            return

        speaker_topic_type = await self.select_speaker(self._message_thread)

        await self.publish_message(GroupChatRequestPublishEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @abstractmethod
    async def select_speaker(self, thread: List[GroupChatPublishEvent]) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        ...

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in group chat manager: {type(message)}")
