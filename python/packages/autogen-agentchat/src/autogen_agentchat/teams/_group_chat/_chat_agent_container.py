from typing import Any, AsyncGenerator, List, Mapping

from autogen_core import DefaultTopicId, MessageContext, event, rpc

from ...base import ChatAgent, Response, TaskResult, Team
from ...messages import AgentEvent, BaseChatMessage, ChatMessage
from ...state import ChatAgentContainerState
from ._events import (
    GroupChatAgentResponse,
    GroupChatMessage,
    GroupChatRequestPublish,
    GroupChatReset,
    GroupChatStart,
    GroupChatTeamResponse,
)
from ._sequential_routed_agent import SequentialRoutedAgent


class ChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.base.ChatAgent` or a :class:`autogen_agentchat.base.Team`
    so that it can be used in a group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        output_topic_type (str): The topic type for the output.
        agent (ChatAgent | Team): The agent to delegate message handling to.
    """

    def __init__(self, parent_topic_type: str, output_topic_type: str, agent: ChatAgent | Team) -> None:
        super().__init__(description=agent.description)
        self._parent_topic_type = parent_topic_type
        self._output_topic_type = output_topic_type
        self._agent = agent
        self._message_buffer: List[ChatMessage] = []

    @event
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle a start event by appending the content to the buffer."""
        if message.messages is not None:
            self._message_buffer.extend(message.messages)

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        """Handle an agent response event by appending the content to the buffer."""
        self._message_buffer.append(message.response.chat_message)

    @event
    async def handle_team_response(self, message: GroupChatTeamResponse, ctx: MessageContext) -> None:
        """Handle a team response event by appending the content to the buffer."""
        for msg in message.task_result.messages:
            if isinstance(msg, BaseChatMessage):
                # Only append chat messages.
                self._message_buffer.append(msg)

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        """Handle a reset event by resetting the agent."""
        self._message_buffer.clear()
        if isinstance(self._agent, Team):
            # Reset the team.
            await self._agent.reset()
        else:
            await self._agent.on_reset(ctx.cancellation_token)

    @event
    async def handle_request(self, message: GroupChatRequestPublish, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        # Pass the messages in the buffer to the delegate agent.
        stream: (
            AsyncGenerator[AgentEvent | ChatMessage | Response, None]
            | AsyncGenerator[AgentEvent | ChatMessage | TaskResult, None]
        )
        if isinstance(self._agent, Team):
            stream = self._agent.run_stream(task=self._message_buffer, cancellation_token=ctx.cancellation_token)
        else:
            stream = self._agent.on_messages_stream(
                messages=self._message_buffer,
                cancellation_token=ctx.cancellation_token,
            )
        final_event: GroupChatAgentResponse | GroupChatTeamResponse | None = None
        count = 0
        async for msg in stream:
            if isinstance(msg, TaskResult):
                # NOTE: a hack here to make sure we don't emit the task messages as part of the response.
                msg.messages = msg.messages[len(self._message_buffer) :]
                final_event = GroupChatTeamResponse(task_result=msg)
            elif isinstance(msg, Response):
                final_event = GroupChatAgentResponse(response=msg)
                # Log the chat message.
                await self.publish_message(
                    GroupChatMessage(message=msg.chat_message),
                    topic_id=DefaultTopicId(type=self._output_topic_type),
                )
            else:
                count += 1
                if isinstance(self._agent, Team) and count <= len(self._message_buffer):
                    # Skip the task messages if this is a team.
                    # NOTE: a hack here to make sure we don't emit the task messages as part of the response.
                    # TODO: we need to fix this in the group chat team implementation and make sure we don't
                    # include the task messages in the final TaskResult.messages.
                    continue
                # Log the message.
                await self.publish_message(
                    GroupChatMessage(message=msg), topic_id=DefaultTopicId(type=self._output_topic_type)
                )
        if final_event is None:
            raise RuntimeError("The contained agent did not produce a final response. Please check implementation.")

        # Publish the response to the group chat.
        self._message_buffer.clear()
        await self.publish_message(
            final_event,
            topic_id=DefaultTopicId(type=self._parent_topic_type),
            cancellation_token=ctx.cancellation_token,
        )

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in agent container: {type(message)}")

    async def save_state(self) -> Mapping[str, Any]:
        agent_state = await self._agent.save_state()
        state = ChatAgentContainerState(agent_state=agent_state, message_buffer=list(self._message_buffer))
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        container_state = ChatAgentContainerState.model_validate(state)
        self._message_buffer = list(container_state.message_buffer)
        await self._agent.load_state(container_state.agent_state)
