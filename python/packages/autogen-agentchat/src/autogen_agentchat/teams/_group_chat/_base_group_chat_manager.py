from abc import ABC, abstractmethod
from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ...base import TerminationCondition
from ...messages import AgentMessage, StopMessage
from ._events import (
    GroupChatAgentResponse,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatStart,
    GroupChatTermination,
)
from ._sequential_routed_agent import SequentialRoutedAgent


class BaseGroupChatManager(SequentialRoutedAgent, ABC):
    """Base class for a group chat manager that manages a group chat with multiple participants.

    It is the responsibility of the caller to ensure:
    - All participants must subscribe to the group chat topic and each of their own topics.
    - The group chat manager must subscribe to the group chat topic.
    - The agent types of the participants must be unique.
    - For each participant, the agent type must be the same as the topic type.

    Without the above conditions, the group chat will not function correctly.
    """

    def __init__(
        self,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None = None,
    ):
        super().__init__(description="Group chat manager")
        self._group_topic_type = group_topic_type
        self._output_topic_type = output_topic_type
        if len(participant_topic_types) != len(participant_descriptions):
            raise ValueError("The number of participant topic types, agent types, and descriptions must be the same.")
        if len(set(participant_topic_types)) != len(participant_topic_types):
            raise ValueError("The participant topic types must be unique.")
        if group_topic_type in participant_topic_types:
            raise ValueError("The group topic type must not be in the participant topic types.")
        self._participant_topic_types = participant_topic_types
        self._participant_descriptions = participant_descriptions
        self._message_thread: List[AgentMessage] = []
        self._termination_condition = termination_condition

    @event
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle the start of a group chat by selecting a speaker to start the conversation."""

        # Check if the conversation has already terminated.
        if self._termination_condition is not None and self._termination_condition.terminated:
            early_stop_message = StopMessage(
                content="The group chat has already terminated.", source="Group chat manager"
            )
            await self.publish_message(
                GroupChatTermination(message=early_stop_message), topic_id=DefaultTopicId(type=self._output_topic_type)
            )
            # Stop the group chat.
            return

        if message.message is not None:
            # Log the start message.
            await self.publish_message(message, topic_id=DefaultTopicId(type=self._output_topic_type))

            # Append the user message to the message thread.
            self._message_thread.append(message.message)

            # Check if the conversation should be terminated.
            if self._termination_condition is not None:
                stop_message = await self._termination_condition([message.message])
                if stop_message is not None:
                    await self.publish_message(
                        GroupChatTermination(message=stop_message),
                        topic_id=DefaultTopicId(type=self._output_topic_type),
                    )
                    # Stop the group chat.
                    return

        speaker_topic_type = await self.select_speaker(self._message_thread)
        await self.publish_message(GroupChatRequestPublish(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        # Append the message to the message thread and construct the delta.
        delta: List[AgentMessage] = []
        if message.agent_response.inner_messages is not None:
            for inner_message in message.agent_response.inner_messages:
                self._message_thread.append(inner_message)
                delta.append(inner_message)
        self._message_thread.append(message.agent_response.chat_message)
        delta.append(message.agent_response.chat_message)

        # Check if the conversation should be terminated.
        if self._termination_condition is not None:
            stop_message = await self._termination_condition(delta)
            if stop_message is not None:
                await self.publish_message(
                    GroupChatTermination(message=stop_message), topic_id=DefaultTopicId(type=self._output_topic_type)
                )
                # Stop the group chat.
                return

        # Select a speaker to continue the conversation.
        speaker_topic_type = await self.select_speaker(self._message_thread)
        await self.publish_message(GroupChatRequestPublish(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @event
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        # Reset the group chat manager.
        await self.reset()

    @abstractmethod
    async def select_speaker(self, thread: List[AgentMessage]) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the group chat manager."""
        ...

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in group chat manager: {type(message)}")
