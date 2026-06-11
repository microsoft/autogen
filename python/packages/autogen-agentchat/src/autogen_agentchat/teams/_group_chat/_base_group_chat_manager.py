import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Dict
from autogen_core import CancellationToken, DefaultTopicId, MessageContext, event, rpc

from ...base import TerminationCondition
from ...messages import BaseAgentEvent, BaseChatMessage, MessageFactory, SelectSpeakerEvent, StopMessage
from ._events import (
    GroupChatAgentResponse,
    GroupChatError,
    GroupChatMessage,
    GroupChatPause,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatResume,
    GroupChatStart,
    GroupChatTeamResponse,
    GroupChatTermination,
    SerializableException,
)
from ._sequential_routed_agent import SequentialRoutedAgent

logger = logging.getLogger(__name__)

class BaseGroupChatManager(SequentialRoutedAgent, ABC):
    """Base class for a group chat manager that manages a group chat with multiple participants.
    
    Liveness Fix: Implements a timeout mechanism for active speakers to prevent
    infinite hangs if a participant fails to respond.
    """

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        emit_team_events: bool = False,
        speaker_timeout: float = 60.0,
    ):
        super().__init__(
            description="Group chat manager",
            sequential_message_types=[
                GroupChatStart,
                GroupChatAgentResponse,
                GroupChatTeamResponse,
                GroupChatMessage,
                GroupChatReset,
            ],
        )
        if max_turns is not None and max_turns <= 0:
            raise ValueError("The maximum number of turns must be greater than 0.")
        if len(participant_topic_types) != len(participant_descriptions):
            raise ValueError("The number of participant topic types, agent types, and descriptions must be the same.")
        if len(set(participant_topic_types)) != len(participant_topic_types):
            raise ValueError("The participant topic types must be unique.")
        if group_topic_type in participant_topic_types:
            raise ValueError("The group topic type must not be in the participant topic types.")
        
        self._name = name
        self._group_topic_type = group_topic_type
        self._output_topic_type = output_topic_type
        self._participant_names = participant_names
        self._participant_name_to_topic_type = {
            name: topic_type for name, topic_type in zip(participant_names, participant_topic_types, strict=True)
        }
        self._participant_descriptions = participant_descriptions
        self._message_thread: List[BaseAgentEvent | BaseChatMessage] = []
        self._output_message_queue = output_message_queue
        self._termination_condition = termination_condition
        self._max_turns = max_turns
        self._current_turn = 0
        self._message_factory = message_factory
        self._emit_team_events = emit_team_events
        self._active_speakers: List[str] = []
        self._active_speakers_timers: Dict[str, float] = {}
        self._speaker_timeout = speaker_timeout
        self._watchdog_task: asyncio.Task | None = None

    @rpc
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        if self._termination_condition is not None and self._termination_condition.terminated:
            early_stop_message = StopMessage(
                content="The group chat has already terminated.",
                source=self._name,
            )
            await self._signal_termination(early_stop_message)
            return

        await self.validate_group_state(message.messages)

        if message.messages is not None:
            await self.publish_message(
                GroupChatStart(messages=message.messages),
                topic_id=DefaultTopicId(type=self._output_topic_type),
            )
            if message.output_task_messages:
                for msg in message.messages:
                    await self._output_message_queue.put(msg)
            await self.publish_message(
                GroupChatStart(messages=message.messages),
                topic_id=DefaultTopicId(type=self._group_topic_type),
                cancellation_token=ctx.cancellation_token,
            )
            await self.update_message_thread(message.messages)
            if await self._apply_termination_condition(message.messages):
                return

        # Start watchdog before selecting first speakers
        await self._start_watchdog(ctx.cancellation_token)
        await self._transition_to_next_speakers(ctx.cancellation_token)

    @event
    async def handle_agent_response(
        self, message: GroupChatAgentResponse | GroupChatTeamResponse, ctx: MessageContext
    ) -> None:
        try:
            delta: List[BaseAgentEvent | BaseChatMessage] = []
            if isinstance(message, GroupChatAgentResponse):
                if message.response.inner_messages is not None:
                    for inner_message in message.response.inner_messages:
                        delta.append(inner_message)
                delta.append(message.response.chat_message)
            else:
                delta.extend(message.result.messages)

            await self.update_message_thread(delta)

            # Remove agent and their timer
            if message.name in self._active_speakers:
                self._active_speakers.remove(message.name)
                self._active_speakers_timers.pop(message.name, None)

            if len(self._active_speakers) > 0:
                return

            if await self._apply_termination_condition(delta, increment_turn_count=True):
                return

            await self._transition_to_next_speakers(ctx.cancellation_token)
        except Exception as e:
            error = SerializableException.from_exception(e)
            await self._signal_termination_with_error(error)
            raise

    async def _transition_to_next_speakers(self, cancellation_token: CancellationToken) -> None:
        speaker_names_future = asyncio.ensure_future(self.select_speaker(self._message_thread))
        cancellation_token.link_future(speaker_names_future)
        speaker_names = await speaker_names_future
        if isinstance(speaker_names, str):
            speaker_names = [speaker_names]
        
        for speaker_name in speaker_names:
            if speaker_name not in self._participant_name_to_topic_type:
                raise RuntimeError(f"Speaker {speaker_name} not found in participant names.")
        
        await self._log_speaker_selection(speaker_names)

        for speaker_name in speaker_names:
            speaker_topic_type = self._participant_name_to_topic_type[speaker_name]
            await self.publish_message(
                GroupChatRequestPublish(),
                topic_id=DefaultTopicId(type=speaker_topic_type),
                cancellation_token=cancellation_token,
            )
            self._active_speakers.append(speaker_name)
            self._active_speakers_timers[speaker_name] = time.monotonic()

    async def _start_watchdog(self, cancellation_token: CancellationToken) -> None:
        """Start the background watchdog task to monitor speaker timeouts."""
        if self._watchdog_task and not self._watchdog_task.done():
            return
        
        self._watchdog_task = asyncio.create_task(self._watchdog_loop(cancellation_token))

    async def _watchdog_loop(self, cancellation_token: CancellationToken) -> None:
        """Periodically check for timed-out speakers."""
        try:
            while True:
                await asyncio.sleep(1.0)
                if cancellation_token.is_cancelled():
                    break
                
                if not self._active_speakers:
                    continue
                
                now = time.monotonic()
                timed_out = [s for s, t in self._active_speakers_timers.items() if now - t > self._speaker_timeout]
                
                if timed_out:
                    logger.warning(f"Speaker(s) {timed_out} timed out after {self._speaker_timeout}s")
                    for s in timed_out:
                        if s in self._active_speakers:
                            self._active_speakers.remove(s)
                        self._active_speakers_timers.pop(s, None)
                    
                    # If all speakers timed out or we are now empty, force transition
                    if not self._active_speakers:
                        logger.info("All active speakers timed out. Forcing transition to next turn.")
                        # We need a cancellation token for transition. 
                        # In a real scenario, we'd pass the original context token.
                        await self._transition_to_next_speakers(cancellation_token)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Watchdog loop encountered an error: %s", e)

    async def _apply_termination_condition(
        self, delta: Sequence[BaseAgentEvent | BaseChatMessage], increment_turn_count: bool = False
    ) -> bool:
        if self._termination_condition is not None:
            stop_message = await self._termination_condition(delta)
            if stop_message is not None:
                await self._termination_condition.reset()
                self._current_turn = 0
                await self._signal_termination(stop_message)
                return True
        if increment_turn_count:
            self._current_turn += 1
        if self._max_turns is not None:
            if self._current_turn >= self._max_turns:
                stop_message = StopMessage(
                    content=f"Maximum number of turns {self._max_turns} reached.",
                    source=self._name,
                )
                if self._termination_condition is not None:
                    await self._termination_condition.reset()
                self._current_turn = 0
                await self._signal_termination(stop_message)
                return True
        return False

    async def _log_speaker_selection(self, speaker_names: List[str]) -> None:
        select_msg = SelectSpeakerEvent(content=speaker_names, source=self._name)
        if self._emit_team_events:
            await self.publish_message(
                GroupChatMessage(message=select_msg),
                topic_id=DefaultTopicId(type=self._output_topic_type),
            )
            await self._output_message_queue.put(select_msg)

    async def _signal_termination(self, message: StopMessage) -> None:
        termination_event = GroupChatTermination(message=message)
        await self.publish_message(
            termination_event,
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        await self._output_message_queue.put(termination_event)

    async def _signal_termination_with_error(self, error: SerializableException) -> None:
        termination_event = GroupChatTermination(
            message=StopMessage(content="An error occurred in the group chat.", source=self._name), error=error
        )
        await self.publish_message(
            termination_event,
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        await self._output_message_queue.put(termination_event)

    @event
    async def handle_group_chat_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        await self._output_message_queue.put(message.message)

    @event
    async def handle_group_chat_error(self, message: GroupChatError, ctx: MessageContext) -> None:
        await self._signal_termination_with_error(message.error)

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        await self.reset()

    @rpc
    async def handle_pause(self, message: GroupChatPause, ctx: MessageContext) -> None:
        pass

    @rpc
    async def handle_resume(self, message: GroupChatResume, ctx: MessageContext) -> None:
        pass

    @abstractmethod
    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        ...

    async def update_message_thread(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        self._message_thread.extend(messages)

    @abstractmethod
    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str:
        ...

    async def reset(self) -> None:
        self._active_speakers = []
        self._active_speakers_timers = {}
        self._current_turn = 0
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
