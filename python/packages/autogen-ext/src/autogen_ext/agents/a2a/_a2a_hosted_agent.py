import json
import uuid
from typing import Sequence, List, AsyncGenerator, Optional

from a2a.client import A2AClient
from a2a.types import AgentCard, SendMessageRequest, MessageSendParams, Message, Role, TextPart, Part, DataPart, \
    FilePart, FileWithBytes, JSONRPCErrorResponse, TaskState, SendStreamingMessageRequest, \
    TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, HandoffMessage, StructuredMessage, TextMessage, \
    MultiModalMessage, BaseAgentEvent, BaseTextChatMessage
from autogen_core import Component, CancellationToken, Image
from httpx import AsyncClient
from pydantic import BaseModel

from ._a2a_deserializer import A2aDeserializer
from slugify import slugify

def get_last_agent_message(messages: List[Message]) -> Message:
    """
    Get the last agent message from the sequence of messages.
    This is used to determine the last response from the agent.
    """
    for message in reversed(messages):
        if message.role == Role.agent:
            return message
    raise RuntimeError(f"No agent messages found: {messages}")

class A2aHostedAgentConfig(BaseModel):
    """Declarative configuration for the A2aHostedAgent."""
    taskId: str
    agentCard: AgentCard
    deserializer: A2aDeserializer | None = None
    http_kwargs: dict = {}
    handoff_message: str | None = None

class A2aHostedAgent(BaseChatAgent, Component[A2aHostedAgentConfig]):

    def __init__(self, agent_card: AgentCard, deserializer: A2aDeserializer = None, http_kwargs: dict = None, handoff_message: str = None):
        super().__init__(name="A2aHostedAgent", description="A hosted agent for A2A operations.")
        self._default_http_kwargs = http_kwargs if http_kwargs is not None else dict()
        self._agent_card = agent_card
        self._task_id = str(uuid.uuid4())
        self._deserializer = deserializer if deserializer is not None else A2aDeserializer(agent_card)
        self._handoff_message = handoff_message if handoff_message is not None else """Transferred to {target}, adopting the role of {target} immediately."""

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
        """Find the HandoffMessage in the message sequence that addresses this agent."""
        if len(messages) > 0 and isinstance(messages[-1], HandoffMessage):
            if messages[-1].target == self.name:
                return messages[-1]
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

    async def call_agent(self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage= None) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response]:
        """Call the LLM with the given parameters."""

        async with AsyncClient(**self._default_http_kwargs) as httpx_client:
            a2a_client = A2AClient(httpx_client, self._agent_card)
            response = await a2a_client.send_message(
                request=SendMessageRequest(id=str(uuid.uuid4()), params=params))
        if isinstance(response.root, JSONRPCErrorResponse):
            raise Exception(f"Error in A2A response: {response.root.error.message}", response.root.error.code,
                            response.root.error.data)

        if response.root.result.status.state == TaskState.canceled:
            cancellation_token.cancel()
        if response.root.result.status.state == TaskState.failed:
            raise RuntimeError(f"Task failed with error: {response.root.result.status.message}")

        messages = []
        for message in response.root.result.history:
            converted_message = self._deserializer.handle_message(message)
            if converted_message is not None:
                messages.append(self._deserializer.handle_message(message))

        if len(messages) == 0:
            raise AssertionError("No agent messages found in the response.")

        for msg in messages:
            yield msg
        if response.root.result.status.state == TaskState.input_required and handoff:
            yield HandoffMessage(content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source) # Handoff to the last agent

    async def call_agent_stream(self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage= None) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response]:
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
                    event = self._deserializer.handle_artifact(response.root.result.artifact)
                    if event is not None:
                        yield event
                converted_message = None
                if isinstance(response.root.result, Message):
                    # Handle the message as a response
                    converted_message = self._deserializer.handle_message(response.root.result)
                if isinstance(response.root.result, TaskStatusUpdateEvent):
                    # Handle the task status update event
                    if response.root.result.status.message is not None:
                        converted_message = self._deserializer.handle_message(response.root.result.status.message)
                    if response.root.result.final is True:
                        final_state = response.root.result.status.state
                if converted_message is not None:
                    yield converted_message
                    last_message = converted_message

        if final_state == TaskState.canceled:
            cancellation_token.cancel()
        if final_state == TaskState.failed:
            raise RuntimeError(
                f"Task failed with error: {last_message.to_text() if last_message is not None else 'Unknown error'}")

        if final_state == TaskState.input_required and handoff:
            yield HandoffMessage(content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source) # Handoff to the last agent

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the agent state."""
        self._task_id = str(uuid.uuid4())