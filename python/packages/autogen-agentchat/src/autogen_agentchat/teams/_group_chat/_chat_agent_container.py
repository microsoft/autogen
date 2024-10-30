from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ...base import ChatAgent
from ...messages import ChatMessage
from .._events import GroupChatPublishEvent, GroupChatRequestPublishEvent
from ._sequential_routed_agent import SequentialRoutedAgent


class ChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.base.ChatAgent` so that it can be used in a
    group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        output_topic_type (str): The topic type for the output.
        agent (ChatAgent): The agent to delegate message handling to.
    """

    def __init__(self, parent_topic_type: str, output_topic_type: str, agent: ChatAgent) -> None:
        super().__init__(description=agent.description)
        self._parent_topic_type = parent_topic_type
        self._output_topic_type = output_topic_type
        self._agent = agent
        self._message_buffer: List[ChatMessage] = []

    @event
    async def handle_message(self, message: GroupChatPublishEvent, ctx: MessageContext) -> None:
        """Handle an event by appending the content to the buffer."""
        self._message_buffer.append(message.agent_message)

    @event
    async def handle_content_request(self, message: GroupChatRequestPublishEvent, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        # Pass the messages in the buffer to the delegate agent.
        response = await self._agent.on_messages(self._message_buffer, ctx.cancellation_token)
        if not any(isinstance(response.chat_message, msg_type) for msg_type in self._agent.produced_message_types):
            raise ValueError(
                f"The agent {self._agent.name} produced an unexpected message type: {type(response)}. "
                f"Expected one of: {self._agent.produced_message_types}. "
                f"Check the agent's produced_message_types property."
            )

        # Publish inner messages to the output topic.
        if response.inner_messages is not None:
            for inner_message in response.inner_messages:
                await self.publish_message(inner_message, topic_id=DefaultTopicId(type=self._output_topic_type))

        # Publish the response.
        self._message_buffer.clear()
        await self.publish_message(
            GroupChatPublishEvent(agent_message=response.chat_message, source=self.id),
            topic_id=DefaultTopicId(type=self._parent_topic_type),
        )

        # Publish the response to the output topic.
        await self.publish_message(response.chat_message, topic_id=DefaultTopicId(type=self._output_topic_type))

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in agent container: {type(message)}")
