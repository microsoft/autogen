import json
import uuid
from typing import Sequence, List, AsyncGenerator, Optional, Self, Mapping, Any, Union

from a2a.client import A2AClient
from a2a.types import AgentCard, SendMessageRequest, MessageSendParams, Message, Role, TextPart, Part, DataPart, \
    FilePart, FileWithBytes, JSONRPCErrorResponse, TaskState, SendStreamingMessageRequest, \
    TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, HandoffMessage, StructuredMessage, TextMessage, \
    MultiModalMessage, BaseAgentEvent, BaseTextChatMessage
from autogen_core import ComponentBase, CancellationToken, Image
from httpx import AsyncClient
from pydantic import BaseModel

from ._a2a_event_mapper import A2aEventMapper
from slugify import slugify


def get_index_of_user_message(messages: List[Message], user_message_params: MessageSendParams) -> int:
    for i, message in enumerate(messages):
        if message.role == Role.user and message.messageId == user_message_params.message.messageId:
            return i
    raise AssertionError("User message not found in the messages list.")

class A2aHostedAgentState(BaseModel):
    task_id: str


class A2aHostedAgentConfig(BaseModel):
    """Declarative configuration for the A2aHostedAgent."""
    agent_card: AgentCard
    event_mapper: A2aEventMapper = None
    http_kwargs: dict = {}
    handoff_message: str = None

class A2aHostedAgent(BaseChatAgent, ComponentBase[A2aHostedAgentConfig]):

    def __init__(self, agent_card: AgentCard, event_mapper: A2aEventMapper = None, http_kwargs: dict = None, handoff_message: str = None):
        super().__init__(name="A2aHostedAgent", description="A hosted agent for A2A operations.")
        self._default_http_kwargs = http_kwargs if http_kwargs is not None else dict()
        self._agent_card = agent_card
        self._task_id = str(uuid.uuid4())
        self._event_mapper = event_mapper if event_mapper is not None else A2aEventMapper(agent_card.name)
        self._handoff_message = handoff_message if handoff_message is not None else "Transferred to {target}, adopting the role of {target} immediately."

    @property
    def name(self) -> str:
        """Return the name of the agent."""
        return slugify(self._agent_card.name)

    @property
    def description(self) -> str:
        """Return the description of the agent."""
        description_builder = [self._agent_card.description]

        if self._agent_card.skills and len(self._agent_card.skills) > 0:
            description_builder.append("Skills: ")
            description_builder.extend([skill.name + " - " + skill.description for skill in self._agent_card.skills])

        return "\n".join(description_builder)

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        message_types: List[type[BaseChatMessage]] = [HandoffMessage, StructuredMessage, TextMessage, MultiModalMessage]
        return tuple(message_types)

    def _build_a2a_message(self, autogen_messages: Sequence[BaseChatMessage]) -> MessageSendParams:
        """
        Build the A2A message from the autogen messages.
        To be overridden by subclasses if any customization is needed in message send params.
        """
        message = Message(
            messageId= str(uuid.uuid4()),
            parts=list(),
            role=Role.user,
            taskId=self._task_id
        )

        for autogen_message in autogen_messages:
            if isinstance(autogen_message, BaseTextChatMessage):
                text = autogen_message.to_text()
                message.parts.append(Part(root=TextPart(text=text)))

            if isinstance(autogen_message, MultiModalMessage):
                for content in autogen_message.content:
                    if isinstance(content, Image):
                        file_part = FilePart(file=FileWithBytes(bytes=content.to_base64()))
                    elif isinstance(content, str):
                        file_part = TextPart(text=content)
                    else:
                        raise AssertionError("Multimodal message content must be an Image or a string.")
                    message.parts.append(Part(root=file_part))

            if isinstance(autogen_message, StructuredMessage):
                data_part = DataPart(data=json.loads(str(autogen_message.to_model_message().content)))
                message.parts.append(Part(root=data_part))

        return MessageSendParams(
            message=message
        )


    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")


    def _get_latest_handoff(self, messages: Sequence[BaseChatMessage]) -> Optional[HandoffMessage]:
        """Find the last HandoffMessage in the message sequence that addresses this agent."""
        for message in reversed(messages):
            if isinstance(message, HandoffMessage):
                if message.target == self.name:
                    return message
                else:
                    raise AssertionError(f"Handoff message target does not match agent name: {messages[-1].source}")
        return None

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        handoff = self._get_latest_handoff(messages)
        params = self._build_a2a_message(messages)

        if not self._agent_card.capabilities.streaming:
            response = self.call_agent(params, cancellation_token, handoff)
        else:
            response = self.call_agent_stream(params, cancellation_token, handoff)
        output_messages = []

        async for message in response:
            if len(output_messages) > 0:
                yield output_messages[-1]
            output_messages.append(message)

        yield Response(
            inner_messages=output_messages[:-1],  # Exclude the last message from inner messages
            chat_message=output_messages[-1]  # Return the last message as the chat message
        )

    async def call_agent(self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage= None) -> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Response], None]:
        """Call the LLM with the given parameters."""

        async with AsyncClient(**self._default_http_kwargs) as httpx_client:
            a2a_client = A2AClient(httpx_client, self._agent_card)
            response = await a2a_client.send_message(
                request=SendMessageRequest(id=str(uuid.uuid4()), params=params))
        if isinstance(response.root, JSONRPCErrorResponse):
            raise Exception(f"Error in A2A response: {response.root.error.message}", response.root.error.code,
                            response.root.error.data)

        history = response.root.result.history[get_index_of_user_message(response.root.result.history, params) + 1:]

        if response.root.result.status.state == TaskState.canceled:
            cancellation_token.cancel()
            return
        if response.root.result.status.state == TaskState.failed:
            raise RuntimeError(f"Task failed with error: {response.root.result.status.message}")

        last_message = None
        for message in history:
            converted_message = self._event_mapper.handle_message(message)
            if converted_message is not None:
                if last_message is not None:
                    yield last_message
                last_message = self._event_mapper.handle_message(message)

        if last_message is None:
            raise AssertionError("No agent messages found in the response.")

        if response.root.result.status.state == TaskState.input_required and handoff:
            yield HandoffMessage(content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source) # Handoff to the last agent

        yield last_message

    async def call_agent_stream(self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage= None) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | Response], None]:
        if not self._agent_card.capabilities.streaming:
            raise RuntimeError("Streaming is not supported by this agent.")
        final_state = None
        request = SendStreamingMessageRequest(id=str(uuid.uuid4()), params=params)
        last_message = None
        async with AsyncClient(**self._default_http_kwargs) as httpx_client:
            a2a_client = A2AClient(httpx_client, self._agent_card)

            async for response in a2a_client.send_message_streaming(request):
                if isinstance(response.root, JSONRPCErrorResponse):
                    raise Exception(f"Error in A2A response: {response.root.error.message}", response.root.error.code,
                                    response.root.error.data)
                if isinstance(response.root.result, TaskArtifactUpdateEvent):
                    # Handle the artifact update event
                    event = self._event_mapper.handle_artifact(response.root.result.artifact)
                    if event is not None:
                        yield event
                converted_message = None
                if isinstance(response.root.result, Message):
                    # Handle the message as a response
                    converted_message = self._event_mapper.handle_message(response.root.result)
                if isinstance(response.root.result, TaskStatusUpdateEvent):
                    # Handle the task status update event
                    if response.root.result.status.message is not None:
                        converted_message = self._event_mapper.handle_message(response.root.result.status.message)
                    if response.root.result.final is True:
                        final_state = response.root.result.status.state
                if converted_message is not None:
                    if last_message is not None:
                        yield last_message
                    last_message = converted_message
        if last_message is None:
            raise AssertionError("No agent messages found in the response.")

        if final_state == TaskState.canceled:
            cancellation_token.cancel()
        if final_state == TaskState.failed:
            raise RuntimeError(
                f"Task failed with error: {last_message.to_text() if last_message is not None else 'Unknown error'}")

        if final_state == TaskState.input_required and handoff:
            yield HandoffMessage(content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source) # Handoff to the last agent

        yield last_message

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the agent state."""
        self._task_id = str(uuid.uuid4())

    async def save_state(self) -> Mapping[str, Any]:
        return A2aHostedAgentState(
            task_id=self._task_id
        ).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore agent from saved state."""
        config = A2aHostedAgentState.model_validate(state)
        self._task_id = config.task_id or str(uuid.uuid4())

    def _to_config(self) -> A2aHostedAgentConfig:
        return A2aHostedAgentConfig(
            agent_card=self._agent_card,
            event_mapper=self._event_mapper,
            http_kwargs=self._default_http_kwargs,
            handoff_message=self._handoff_message
        )

    @classmethod
    def _from_config(cls, config: A2aHostedAgentConfig) -> Self:
        return cls(
            agent_card=config.agent_card,
            event_mapper=config.event_mapper or A2aEventMapper(config.agentCard),
            http_kwargs=config.http_kwargs or {},
            handoff_message=config.handoff_message or "Transferred to {target}, adopting the role of {target} immediately."
        )
