from typing import List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ...base import ChatAgent
from ...messages import ChatMessage, MultiModalMessage, StopMessage, TextMessage, ToolCallMessage
from .._events import ContentPublishEvent, ContentRequestEvent, ToolCallEvent, ToolCallResultEvent
from ._sequential_routed_agent import SequentialRoutedAgent


class BaseChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.agents.BaseChatAgent` so that it can be used in a
    group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        agent (BaseChatAgent): The agent to delegate message handling to.
    """

    def __init__(self, parent_topic_type: str, agent: ChatAgent) -> None:
        super().__init__(description=agent.description)
        self._parent_topic_type = parent_topic_type
        self._agent = agent
        self._message_buffer: List[ChatMessage] = []

    @event
    async def handle_message(
        self, message: ContentPublishEvent | ToolCallEvent | ToolCallResultEvent, ctx: MessageContext
    ) -> None:
        """Handle an event by appending the content to the buffer."""
        self._message_buffer.append(message.agent_message)

    @event
    async def handle_content_request(self, message: ContentRequestEvent, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        # Pass the messages in the buffer to the delegate agent.
        response = await self._agent.on_messages(self._message_buffer, ctx.cancellation_token)

        # Publish the response.
        self._message_buffer.clear()
        if isinstance(response, ToolCallMessage):
            await self.publish_message(
                ToolCallEvent(agent_message=response, source=self.id),
                topic_id=DefaultTopicId(type=self._parent_topic_type),
            )
        elif isinstance(response, TextMessage | MultiModalMessage | StopMessage):
            await self.publish_message(
                ContentPublishEvent(agent_message=response, source=self.id),
                topic_id=DefaultTopicId(type=self._parent_topic_type),
            )
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
