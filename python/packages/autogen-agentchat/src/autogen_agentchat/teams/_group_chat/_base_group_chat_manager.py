import asyncio
from abc import ABC, abstractmethod
from typing import Any, List

from autogen_core import DefaultTopicId, MessageContext, event, rpc

from ...base import TerminationCondition
from ...messages import AgentEvent, ChatMessage, StopMessage
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
        max_turns: int | None = None,
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
        self._message_thread: List[AgentEvent | ChatMessage] = []
        self._termination_condition = termination_condition
        if max_turns is not None and max_turns <= 0:
            raise ValueError("The maximum number of turns must be greater than 0.")
        self._max_turns = max_turns
        self._current_turn = 0

    @rpc
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

        # Validate the group state given the start messages
        await self.validate_group_state(message.messages)

        if message.messages is not None:
            # Log all messages at once
            await self.publish_message(
                GroupChatStart(messages=message.messages), topic_id=DefaultTopicId(type=self._output_topic_type)
            )

            # Relay all messages at once to participants
            await self.publish_message(
                GroupChatStart(messages=message.messages),
                topic_id=DefaultTopicId(type=self._group_topic_type),
                cancellation_token=ctx.cancellation_token,
            )

            # Append all messages to thread
            self._message_thread.extend(message.messages)

            # Check termination condition after processing all messages
            if self._termination_condition is not None:
                stop_message = await self._termination_condition(message.messages)
                if stop_message is not None:
                    await self.publish_message(
                        GroupChatTermination(message=stop_message),
                        topic_id=DefaultTopicId(type=self._output_topic_type),
                    )
                    # Stop the group chat and reset the termination condition.
                    await self._termination_condition.reset()
                    return

        # Select a speaker to start/continue the conversation
        speaker_topic_type_future = asyncio.ensure_future(self.select_speaker(self._message_thread))
        # Link the select speaker future to the cancellation token.
        ctx.cancellation_token.link_future(speaker_topic_type_future)
        speaker_topic_type = await speaker_topic_type_future
        await self.publish_message(
            GroupChatRequestPublish(),
            topic_id=DefaultTopicId(type=speaker_topic_type),
            cancellation_token=ctx.cancellation_token,
        )

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        # Append the message to the message thread and construct the delta.
        delta: List[AgentEvent | ChatMessage] = []
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
                # Stop the group chat and reset the termination conditions and turn count.
                await self._termination_condition.reset()
                self._current_turn = 0
                return

        # Increment the turn count.
        self._current_turn += 1
        # Check if the maximum number of turns has been reached.
        if self._max_turns is not None:
            if self._current_turn >= self._max_turns:
                stop_message = StopMessage(
                    content=f"Maximum number of turns {self._max_turns} reached.",
                    source="Group chat manager",
                )
                await self.publish_message(
                    GroupChatTermination(message=stop_message), topic_id=DefaultTopicId(type=self._output_topic_type)
                )
                # Stop the group chat and reset the termination conditions and turn count.
                if self._termination_condition is not None:
                    await self._termination_condition.reset()
                self._current_turn = 0
                return

        # Select a speaker to continue the conversation.
        speaker_topic_type_future = asyncio.ensure_future(self.select_speaker(self._message_thread))
        # Link the select speaker future to the cancellation token.
        ctx.cancellation_token.link_future(speaker_topic_type_future)
        speaker_topic_type = await speaker_topic_type_future
        await self.publish_message(
            GroupChatRequestPublish(),
            topic_id=DefaultTopicId(type=speaker_topic_type),
            cancellation_token=ctx.cancellation_token,
        )

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        # Reset the group chat manager.
        await self.reset()

    @abstractmethod
    async def validate_group_state(self, messages: List[ChatMessage] | None) -> None:
        """Validate the state of the group chat given the start messages.
        This is executed when the group chat manager receives a GroupChatStart event.

        Args:
            messages: A list of chat messages to validate, or None if no messages are provided.
        """
        ...

    @abstractmethod
    async def select_speaker(self, thread: List[AgentEvent | ChatMessage]) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the group chat manager."""
        ...

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in group chat manager: {type(message)}")
