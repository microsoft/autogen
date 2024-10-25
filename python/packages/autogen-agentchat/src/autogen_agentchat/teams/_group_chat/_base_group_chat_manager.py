import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import List

from autogen_core.base import CancellationToken, MessageContext
from autogen_core.components import DefaultTopicId, FunctionCall, event
from autogen_core.components.models import FunctionExecutionResult
from autogen_core.components.tools import Tool

from ... import EVENT_LOGGER_NAME
from ...base import TerminationCondition
from ...messages import ToolCallResultMessage
from .._events import (
    ContentPublishEvent,
    ContentRequestEvent,
    HandoffEvent,
    TerminationEvent,
    ToolCallEvent,
    ToolCallResultEvent,
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
        tools (List[Tool], optional): The tools used in the group chat. Defaults to None.
            The names of the tools must be unique.

    Raises:
        ValueError: If the number of participant topic types, agent types, and descriptions are not the same.
        ValueError: If the participant topic types are not unique.
        ValueError: If the group topic type is in the participant topic types.
        ValueError: If the parent topic type is in the participant topic types.
        ValueError: If the group topic type is the same as the parent topic type.
        ValueError: If the names of the tools are not unique.
    """

    def __init__(
        self,
        parent_topic_type: str,
        group_topic_type: str,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        termination_condition: TerminationCondition | None = None,
        tools: List[Tool] | None = None,
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
        self._message_thread: List[ContentPublishEvent | ToolCallEvent | ToolCallResultEvent | HandoffEvent] = []
        self._termination_condition = termination_condition
        if tools is not None:
            tool_names = [tool.name for tool in tools]
            if len(tool_names) != len(set(tool_names)):
                raise ValueError("The names of the tools must be unique.")
        self._tools = tools

    @event
    async def handle_tool_call(self, message: ToolCallEvent, ctx: MessageContext) -> None:
        """Handle a tool call event by executing the tool and publishing the result, then
        selecting a speaker to continue the conversation."""
        event_logger.debug(message)
        self._message_thread.append(message)

        # Check if the conversation should be terminated.
        if self._termination_condition is not None:
            stop_message = await self._termination_condition([message.agent_message])
            if stop_message is not None:
                event_logger.info(TerminationEvent(agent_message=stop_message, source=self.id))
                # Stop the group chat.
                return

        # Execute the tool call.
        results = await asyncio.gather(
            *[self._execute_tool_call(call, ctx.cancellation_token) for call in message.agent_message.content]
        )
        feedback = ToolCallResultEvent(
            agent_message=ToolCallResultMessage(content=results, source=self.id.type), source=self.id
        )
        event_logger.debug(feedback)
        await self.publish_message(feedback, topic_id=DefaultTopicId(type=self._group_topic_type))
        self._message_thread.append(feedback)

        # Check if the conversation should be terminated.
        if self._termination_condition is not None:
            stop_message = await self._termination_condition([feedback.agent_message])
            if stop_message is not None:
                event_logger.info(TerminationEvent(agent_message=stop_message, source=self.id))
                # Stop the group chat.
                return

        # Select a speaker to continue the conversation.
        speaker_topic_type = await self.select_speaker(self._message_thread)
        await self.publish_message(ContentRequestEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    async def _execute_tool_call(
        self, tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        """Execute a tool call and return the result."""
        try:
            if self._tools is None:
                raise ValueError("No tools are available.")
            tool = next((t for t in self._tools if t.name == tool_call.name), None)
            if tool is None:
                raise ValueError(f"The tool '{tool_call.name}' is not available.")
            arguments = json.loads(tool_call.arguments)
            result = await tool.run_json(arguments, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
            return FunctionExecutionResult(content=result_as_str, call_id=tool_call.id)
        except Exception as e:
            return FunctionExecutionResult(content=f"Error: {e}", call_id=tool_call.id)

    @event
    async def handle_handoff(self, message: HandoffEvent, ctx: MessageContext) -> None:
        """Handle a handoff event by selecting a speaker to continue the conversation."""
        event_logger.info(message)
        self._message_thread.append(message)

        if self._termination_condition is not None:
            stop_message = await self._termination_condition([message.agent_message])
            if stop_message is not None:
                event_logger.info(TerminationEvent(agent_message=stop_message, source=self.id))
                # Stop the group chat.
                return

        if message.agent_message.content not in self._participant_topic_types:
            raise ValueError("The handoff message must be to a participant.")

        # Select a speaker to continue the conversation.
        speaker_topic_type = await self.select_speaker(self._message_thread)
        await self.publish_message(ContentRequestEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @event
    async def handle_content_publish(self, message: ContentPublishEvent, ctx: MessageContext) -> None:
        """Handle a content publish event.

        If the event is from the parent topic, add the message to the thread.

        If the event is from the group chat topic, add the message to the thread and select a speaker to continue the conversation.
        If the event from the group chat session requests a pause, publish the last message to the parent topic."""
        assert ctx.topic_id is not None

        event_logger.info(message)

        # Process event from parent.
        if ctx.topic_id.type == self._parent_topic_type:
            self._message_thread.append(message)
            await self.publish_message(
                ContentPublishEvent(agent_message=message.agent_message, source=self.id),
                topic_id=DefaultTopicId(type=self._group_topic_type),
            )
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

        await self.publish_message(ContentRequestEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @event
    async def handle_content_request(self, message: ContentRequestEvent, ctx: MessageContext) -> None:
        """Handle a content request by selecting a speaker to start the conversation."""
        assert ctx.topic_id is not None
        if ctx.topic_id.type == self._group_topic_type:
            raise RuntimeError("Content request event from the group chat topic is not allowed.")

        speaker_topic_type = await self.select_speaker(self._message_thread)

        await self.publish_message(ContentRequestEvent(), topic_id=DefaultTopicId(type=speaker_topic_type))

    @abstractmethod
    async def select_speaker(
        self, thread: List[ContentPublishEvent | ToolCallEvent | ToolCallResultEvent | HandoffEvent]
    ) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        ...
