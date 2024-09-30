from typing import List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ...agents import BaseChatAgent, MultiModalMessage, StopMessage, TextMessage
from ._events import ContentPublishEvent, ContentRequestEvent
from ._sequential_routed_agent import SequentialRoutedAgent


class BaseChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.agents.BaseChatAgent` so that it can be used in a
    group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        agent (BaseChatAgent): The agent to delegate message handling to.
    """

    def __init__(self, parent_topic_type: str, agent: BaseChatAgent) -> None:
        super().__init__(description=agent.description)
        self._parent_topic_type = parent_topic_type
        self._agent = agent
        self._message_buffer: List[TextMessage | MultiModalMessage | StopMessage] = []

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
        # TODO: handle tool call messages.
        assert isinstance(response, TextMessage | MultiModalMessage | StopMessage)
        self._message_buffer.clear()
        await self.publish_message(
            ContentPublishEvent(agent_message=response), topic_id=DefaultTopicId(type=self._parent_topic_type)
        )
