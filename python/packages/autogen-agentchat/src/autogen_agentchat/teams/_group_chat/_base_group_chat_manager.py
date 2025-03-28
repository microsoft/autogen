import asyncio
from abc import ABC, abstractmethod
from typing import Any, List
from asyncio import Lock

from autogen_core import DefaultTopicId, MessageContext, event, rpc

from ...base import TerminationCondition
from ...messages import AgentEvent, ChatMessage, MessageFactory, StopMessage
from ._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatPause,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatResume,
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
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[AgentEvent | ChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
    ):
        super().__init__(
            description="Group chat manager",
            sequential_message_types=[
                GroupChatStart,
                GroupChatAgentResponse,
                GroupChatMessage,
                GroupChatReset,
            ],
        )
        self._name = name
        self._group_topic_type = group_topic_type
        self._output_topic_type = output_topic_type
        if len(participant_topic_types) != len(participant_descriptions):
            raise ValueError("The number of participant topic types, agent types, and descriptions must be the same.")
        if len(set(participant_topic_types)) != len(participant_topic_types):
            raise ValueError("The participant topic types must be unique.")
        if group_topic_type in participant_topic_types:
            raise ValueError("The group topic type must not be in the participant topic types.")
        self._participant_names = participant_names
        self._participant_name_to_topic_type = {
            name: topic_type for name, topic_type in zip(participant_names, participant_topic_types, strict=True)
        }
        self._participant_descriptions = participant_descriptions
        self._message_thread: List[AgentEvent | ChatMessage] = []
        self._output_message_queue = output_message_queue
        self._termination_condition = termination_condition
        if max_turns is not None and max_turns <= 0:
            raise ValueError("The maximum number of turns must be greater than 0.")
        self._max_turns = max_turns
        self._current_turn = 0
        self._message_factory = message_factory
        self._lock = Lock()

    @rpc
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle the start of a group chat by selecting a speaker to start the conversation."""

        # Check if the conversation has already terminated.
        if self._termination_condition is not None and self._termination_condition.terminated:
            early_stop_message = StopMessage(
                content="The group chat has already terminated.",
                source=self._name,
            )
            # Signal termination to the caller of the team.
            await self._signal_termination(early_stop_message)
            # Stop the group chat.
            return

        # Validate the group state given the start messages
        await self.validate_group_state(message.messages)

        if message.messages is not None:
            # Log all messages at once
            await self.publish_message(
                GroupChatStart(messages=message.messages),
                topic_id=DefaultTopicId(type=self._output_topic_type),
            )
            for msg in message.messages:
                await self._output_message_queue.put(msg)

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
                    # Reset the termination condition.
                    await self._termination_condition.reset()
                    # Signal termination to the caller of the team.
                    await self._signal_termination(stop_message)
                    # Stop the group chat.
                    return
                
        # Select multiple speakers concurrently
        speaker_names_future = asyncio.ensure_future(self.select_speakers(self._message_thread))

        # Link the future to the cancellation token
        ctx.cancellation_token.link_future(speaker_names_future)
        
        # Await the speakers list
        speaker_names = await speaker_names_future
        # Validate all speakers before proceeding
        invalid_speakers = [name for name in speaker_names if name not in self._participant_name_to_topic_type]
        if invalid_speakers:
            raise RuntimeError(f"Speakers {invalid_speakers} not found in participant names.")
        
        # Get topic types for each speaker
        speaker_topic_map = {
            name: self._participant_name_to_topic_type[name] for name in speaker_names
        }

        # Publish messages concurrently for all speakers
        await asyncio.gather(*[
            self.publish_message(
                GroupChatRequestPublish(),
                topic_id=DefaultTopicId(type=topic_type),
                cancellation_token=ctx.cancellation_token,
            )
            for topic_type in speaker_topic_map.values()
        ])


    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        async with self._lock:
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
                    # Reset the termination conditions and turn count.
                    await self._termination_condition.reset()
                    self._current_turn = 0
                    # Signal termination to the caller of the team.
                    await self._signal_termination(stop_message)
                    # Stop the group chat.
                    return

            # Increment the turn count.
            self._current_turn += 1
            # Check if the maximum number of turns has been reached.
            if self._max_turns is not None:
                if self._current_turn >= self._max_turns:
                    stop_message = StopMessage(
                        content=f"Maximum number of turns {self._max_turns} reached.",
                        source=self._name,
                    )
                    # Reset the termination conditions and turn count.
                    if self._termination_condition is not None:
                        await self._termination_condition.reset()
                    self._current_turn = 0
                    # Signal termination to the caller of the team.
                    await self._signal_termination(stop_message)
                    # Stop the group chat.
                    return

            # Select multiple speakers concurrently
            speaker_names_future = asyncio.ensure_future(self.select_speakers(self._message_thread))

            # Link the future to the cancellation token
            ctx.cancellation_token.link_future(speaker_names_future)
            
            # Await the speakers list
            speaker_names = await speaker_names_future
            # Validate all speakers before proceeding
            invalid_speakers = [name for name in speaker_names if name not in self._participant_name_to_topic_type]
            if invalid_speakers:
                raise RuntimeError(f"Speakers {invalid_speakers} not found in participant names.")

            if speaker_names:
                # Get topic types for each speaker
                speaker_topic_map = {
                    name: self._participant_name_to_topic_type[name] for name in speaker_names
                }

                # Publish messages concurrently for all speakers
                await asyncio.gather(*[
                    self.publish_message(
                        GroupChatRequestPublish(),
                        topic_id=DefaultTopicId(type=topic_type),
                        cancellation_token=ctx.cancellation_token,
                    )
                    for topic_type in speaker_topic_map.values()
                ])


    async def _signal_termination(self, message: StopMessage) -> None:
        termination_event = GroupChatTermination(message=message)
        # Log the early stop message.
        await self.publish_message(
            termination_event,
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        # Put the termination event in the output message queue.
        await self._output_message_queue.put(termination_event)

    @event
    async def handle_group_chat_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        """Handle a group chat message by appending the content to its output message queue."""
        await self._output_message_queue.put(message.message)

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        """Reset the group chat manager. Calling :meth:`reset` to reset the group chat manager
        and clear the message thread."""
        await self.reset()

    @rpc
    async def handle_pause(self, message: GroupChatPause, ctx: MessageContext) -> None:
        """Pause the group chat manager. This is a no-op in the base class."""
        pass

    @rpc
    async def handle_resume(self, message: GroupChatResume, ctx: MessageContext) -> None:
        """Resume the group chat manager. This is a no-op in the base class."""
        pass

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

    async def select_speakers(self, thread: List[AgentEvent | ChatMessage]) -> List[str]:
        """Select multiple speakers from the participants and return the
        topic types of the selected speakers."""
        speaker = await self.select_speaker(thread)  # ✅ Ensure we await the result
        return [speaker] 

    @abstractmethod
    async def reset(self) -> None:
        """Reset the group chat manager."""
        ...

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in group chat manager: {type(message)}")
