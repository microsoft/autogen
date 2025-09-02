from typing import Any, List, Mapping

from autogen_core import DefaultTopicId, MessageContext, event, rpc, trace_invoke_agent_span

from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, MessageFactory, TextMessage

from ...base import ChatAgent, Response, TaskResult, Team
from ...state import ChatAgentContainerState
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
    SerializableException,
)
from ._sequential_routed_agent import SequentialRoutedAgent


class ChatAgentContainer(SequentialRoutedAgent):
    """A core agent class that delegates message handling to an
    :class:`autogen_agentchat.base.ChatAgent` or :class:`autogen_agentchat.base.Team`
    so that it can be used in a group chat team.

    Args:
        parent_topic_type (str): The topic type of the parent orchestrator.
        output_topic_type (str): The topic type for the output.
        agent (ChatAgent | Team): The agent or team to delegate message handling to.
        message_factory (MessageFactory): The message factory to use for
            creating messages from JSON data.
    """

    def __init__(
        self, parent_topic_type: str, output_topic_type: str, agent: ChatAgent | Team, message_factory: MessageFactory
    ) -> None:
        super().__init__(
            description=agent.description,
            sequential_message_types=[
                GroupChatStart,
                GroupChatRequestPublish,
                GroupChatReset,
                GroupChatAgentResponse,
                GroupChatTeamResponse,
            ],
        )
        self._parent_topic_type = parent_topic_type
        self._output_topic_type = output_topic_type
        self._agent = agent
        self._message_buffer: List[BaseChatMessage] = []
        self._message_factory = message_factory

    @event
    async def handle_start(self, message: GroupChatStart, ctx: MessageContext) -> None:
        """Handle a start event by appending the content to the buffer."""
        if message.messages is not None:
            for msg in message.messages:
                self._buffer_message(msg)

    @event
    async def handle_agent_response(self, message: GroupChatAgentResponse, ctx: MessageContext) -> None:
        """Handle an agent response event by appending the content to the buffer."""
        self._buffer_message(message.response.chat_message)

    @event
    async def handle_team_response(self, message: GroupChatTeamResponse, ctx: MessageContext) -> None:
        """Handle a team response event by appending the content to the buffer."""
        for msg in message.result.messages:
            if isinstance(msg, BaseChatMessage):
                self._buffer_message(msg)

    @rpc
    async def handle_reset(self, message: GroupChatReset, ctx: MessageContext) -> None:
        """Handle a reset event by resetting the agent."""
        self._message_buffer.clear()
        if isinstance(self._agent, Team):
            # If the agent is a team, reset the team.
            await self._agent.reset()
        else:
            await self._agent.on_reset(ctx.cancellation_token)

    @event
    async def handle_request(self, message: GroupChatRequestPublish, ctx: MessageContext) -> None:
        """Handle a content request event by passing the messages in the buffer
        to the delegate agent and publish the response."""
        if isinstance(self._agent, Team):
            try:
                stream = self._agent.run_stream(
                    task=self._message_buffer,
                    cancellation_token=ctx.cancellation_token,
                    output_task_messages=False,
                )
                result: TaskResult | None = None
                async for team_event in stream:
                    if isinstance(team_event, TaskResult):
                        result = team_event
                    else:
                        await self._log_message(team_event)
                if result is None:
                    raise RuntimeError(
                        "The team did not produce a final TaskResult. Check the team's run_stream method."
                    )
                self._message_buffer.clear()
                # Publish the team response to the group chat.
                await self.publish_message(
                    GroupChatTeamResponse(result=result, name=self._agent.name),
                    topic_id=DefaultTopicId(type=self._parent_topic_type),
                    cancellation_token=ctx.cancellation_token,
                )
            except Exception as e:
                # Publish the error to the group chat.
                error_message = SerializableException.from_exception(e)
                await self.publish_message(
                    GroupChatError(error=error_message),
                    topic_id=DefaultTopicId(type=self._parent_topic_type),
                    cancellation_token=ctx.cancellation_token,
                )
                # Raise the error to the runtime.
                raise
        else:
            # If the agent is not a team, handle it as a single agent.
            with trace_invoke_agent_span(
                agent_name=self._agent.name,
                agent_description=self._agent.description,
                agent_id=str(self.id),
            ):
                try:
                    # Pass the messages in the buffer to the delegate agent.
                    response: Response | None = None
                    async for msg in self._agent.on_messages_stream(self._message_buffer, ctx.cancellation_token):
                        if isinstance(msg, Response):
                            await self._log_message(msg.chat_message)
                            response = msg
                        else:
                            await self._log_message(msg)
                    if response is None:
                        raise RuntimeError(
                            "The agent did not produce a final response. Check the agent's on_messages_stream method."
                        )
                    # Publish the response to the group chat.
                    self._message_buffer.clear()
                    await self.publish_message(
                        GroupChatAgentResponse(response=response, name=self._agent.name),
                        topic_id=DefaultTopicId(type=self._parent_topic_type),
                        cancellation_token=ctx.cancellation_token,
                    )
                except Exception as e:
                    # Publish the error to the group chat.
                    error_message = SerializableException.from_exception(e)
                    await self.publish_message(
                        GroupChatError(error=error_message),
                        topic_id=DefaultTopicId(type=self._parent_topic_type),
                        cancellation_token=ctx.cancellation_token,
                    )
                    # Raise the error to the runtime.
                    raise

    @rpc
    async def handle_direct_text_message(self, message: TextMessage, ctx: MessageContext) -> Response | GroupChatError:
        with trace_invoke_agent_span(
            agent_name=self._agent.name,
            agent_description=self._agent.description,
            agent_id=str(self.id),
        ):
            try:
                response: Response | None = None
                async for msg in self._agent.on_messages_stream([message], ctx.cancellation_token):
                    if isinstance(msg, Response):
                        response = msg
                if response is None:
                    raise ValueError(
                        "The agent did not produce a final response. Check the agent's on_messages_stream method."
                    )
                return response
            except Exception as e:
                # Publish the error to the group chat.
                error_message = SerializableException.from_exception(e)
                return GroupChatError(error=error_message)

    def _buffer_message(self, message: BaseChatMessage) -> None:
        if not self._message_factory.is_registered(message.__class__):
            raise ValueError(f"Message type {message.__class__} is not registered.")
        # Buffer the message.
        self._message_buffer.append(message)

    async def _log_message(self, message: BaseAgentEvent | BaseChatMessage) -> None:
        if not self._message_factory.is_registered(message.__class__):
            raise ValueError(f"Message type {message.__class__} is not registered.")
        # Log the message.
        await self.publish_message(
            GroupChatMessage(message=message),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )

    @rpc
    async def handle_pause(self, message: GroupChatPause, ctx: MessageContext) -> None:
        """Handle a pause event by pausing the agent."""
        if isinstance(self._agent, Team):
            # If the agent is a team, pause the team.
            await self._agent.pause()
        else:
            await self._agent.on_pause(ctx.cancellation_token)

    @rpc
    async def handle_resume(self, message: GroupChatResume, ctx: MessageContext) -> None:
        """Handle a resume event by resuming the agent."""
        if isinstance(self._agent, Team):
            # If the agent is a team, resume the team.
            await self._agent.resume()
        else:
            await self._agent.on_resume(ctx.cancellation_token)

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        raise ValueError(f"Unhandled message in agent container: {type(message)}")

    async def save_state(self) -> Mapping[str, Any]:
        agent_state = await self._agent.save_state()
        state = ChatAgentContainerState(
            agent_state=agent_state, message_buffer=[message.dump() for message in self._message_buffer]
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        container_state = ChatAgentContainerState.model_validate(state)
        self._message_buffer = []
        for message_data in container_state.message_buffer:
            message = self._message_factory.create(message_data)
            if isinstance(message, BaseChatMessage):
                self._message_buffer.append(message)
            else:
                raise ValueError(f"Invalid message type in message buffer: {type(message)}")
        await self._agent.load_state(container_state.agent_state)
