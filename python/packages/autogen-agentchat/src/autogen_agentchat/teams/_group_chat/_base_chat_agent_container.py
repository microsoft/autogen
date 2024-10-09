import asyncio
import logging
from typing import List

from autogen_core.base import AgentId, AgentType, MessageContext
from autogen_core.components import DefaultTopicId, event
from autogen_core.components.models import FunctionExecutionResult
from autogen_core.components.tool_agent import ToolException

from ...agents import BaseChatAgent, MultiModalMessage, StopMessage, TextMessage, ToolCallMessage, ToolCallResultMessage
from .._events import ContentPublishEvent, ContentRequestEvent, ToolCallEvent, ToolCallResultEvent
from .._logging import EVENT_LOGGER_NAME
from ._sequential_routed_agent import SequentialRoutedAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class BaseChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.agents.BaseChatAgent` so that it can be used in a
    group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        agent (BaseChatAgent): The agent to delegate message handling to.
        tool_agent_type (AgentType, optional): The agent type of the tool agent. Defaults to None.
    """

    def __init__(self, parent_topic_type: str, agent: BaseChatAgent, tool_agent_type: AgentType | None = None) -> None:
        super().__init__(description=agent.description)
        self._parent_topic_type = parent_topic_type
        self._agent = agent
        self._message_buffer: List[TextMessage | MultiModalMessage | StopMessage] = []
        self._tool_agent_id = AgentId(type=tool_agent_type, key=self.id.key) if tool_agent_type else None

    @event
    async def handle_content_publish(self, message: ContentPublishEvent, ctx: MessageContext) -> None:
        """Handle a content publish event by appending the content to the buffer."""
        if not isinstance(message.agent_message, TextMessage | MultiModalMessage | StopMessage):
            raise ValueError(
                f"Unexpected message type: {type(message.agent_message)}. "
                "The message must be a text, multimodal, or stop message."
            )
        self._message_buffer.append(message.agent_message)

    @event
    async def handle_content_request(self, message: ContentRequestEvent, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        response = await self._agent.on_messages(self._message_buffer, ctx.cancellation_token)

        if self._tool_agent_id is not None:
            # Handle tool calls.
            while isinstance(response, ToolCallMessage):
                # Log the tool call.
                event_logger.debug(ToolCallEvent(agent_message=response, source=self.id))

                results: List[FunctionExecutionResult | BaseException] = await asyncio.gather(
                    *[
                        self.send_message(
                            message=call,
                            recipient=self._tool_agent_id,
                            cancellation_token=ctx.cancellation_token,
                        )
                        for call in response.content
                    ]
                )
                # Combine the results in to a single response and handle exceptions.
                function_results: List[FunctionExecutionResult] = []
                for result in results:
                    if isinstance(result, FunctionExecutionResult):
                        function_results.append(result)
                    elif isinstance(result, ToolException):
                        function_results.append(
                            FunctionExecutionResult(content=f"Error: {result}", call_id=result.call_id)
                        )
                    elif isinstance(result, BaseException):
                        raise result  # Unexpected exception.
                # Create a new tool call result message.
                feedback = ToolCallResultMessage(content=function_results, source=self._tool_agent_id.type)
                # Log the feedback.
                event_logger.debug(ToolCallResultEvent(agent_message=feedback, source=self._tool_agent_id))
                response = await self._agent.on_messages([feedback], ctx.cancellation_token)

        # Publish the response.
        assert isinstance(response, TextMessage | MultiModalMessage | StopMessage)
        self._message_buffer.clear()
        await self.publish_message(
            ContentPublishEvent(agent_message=response, source=self.id),
            topic_id=DefaultTopicId(type=self._parent_topic_type),
        )
