from typing import Any, List

from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, event

from ...base import ChatAgent, Response
from ...messages import ChatMessage
from ._events import GroupChatAgentResponse, GroupChatMessage, GroupChatRequestPublish, GroupChatReset, GroupChatStart
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
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle a start event by appending the content to the buffer."""
        if message.message is not None:
            self._message_buffer.append(message.message)

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        """Handle an agent response event by appending the content to the buffer."""
        self._message_buffer.append(message.agent_response.chat_message)

    @event
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        """Handle a reset event by resetting the agent."""
        self._message_buffer.clear()
        await self._agent.reset(ctx.cancellation_token)

    @event
    async def handle_request(self, message: GroupChatRequestPublish, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        # Pass the messages in the buffer to the delegate agent.
        response: Response | None = None
        async for msg in self._agent.on_messages_stream(self._message_buffer, ctx.cancellation_token):
            if isinstance(msg, Response):
                # Log the response.
                await self.publish_message(
                    GroupChatMessage(message=msg.chat_message),
                    topic_id=DefaultTopicId(type=self._output_topic_type),
                )
                response = msg
            else:
                # Log the message.
                await self.publish_message(
                    GroupChatMessage(message=msg), topic_id=DefaultTopicId(type=self._output_topic_type)
                )
        if response is None:
            raise ValueError("The agent did not produce a final response. Check the agent's on_messages_stream method.")

        # Publish the response to the group chat.
        self._message_buffer.clear()
        await self.publish_message(
            GroupChatAgentResponse(agent_response=response),
            topic_id=DefaultTopicId(type=self._parent_topic_type),
        )

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in agent container: {type(message)}")
