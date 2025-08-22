import json
import uuid
from typing import Any, AsyncGenerator, List, Mapping, Optional, Self, Sequence, Union

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    BaseTextChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StructuredMessage,
    TextMessage,
)
from autogen_core import CancellationToken, ComponentBase, Image
from httpx import AsyncClient
from pydantic import BaseModel
from slugify import slugify

from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    DataPart,
    FilePart,
    FileWithBytes,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendStreamingMessageRequest,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)

from ._a2a_event_mapper import A2aEventMapper


def get_index_of_user_message(messages: List[Message], user_message_params: MessageSendParams) -> int:
    """Find the index of a specific user message in a message list.

    Args:
        messages (List[Message]): List of messages to search through
        user_message_params (MessageSendParams): Parameters containing the message to find

    Returns:
        int: Index of the user message in the list

    Raises:
        AssertionError: If the user message is not found in the list

    Example:
        ```python
        messages = [Message(role=Role.user, messageId="123"), Message(role=Role.agent)]
        params = MessageSendParams(message=Message(messageId="123"))
        index = get_index_of_user_message(messages, params)
        # index will be 0
        ```
    """
    for i, message in enumerate(messages):
        if message.role == Role.user and message.messageId == user_message_params.message.messageId:
            return i
    raise AssertionError("User message not found in the messages list.")


class A2aHostedAgentState(BaseModel):
    task_id: str


class A2aHostedAgentConfig(BaseModel):
    """Configuration model for the A2aHostedAgent.

    Args:
        agent_card (AgentCard): The agent card containing agent capabilities and metadata
        event_mapper (A2aEventMapper, optional): Custom event mapper for message conversion
        http_kwargs (dict, optional): Additional HTTP client configuration
        handoff_message (str, optional): Template for handoff messages
    """

    agent_card: AgentCard
    event_mapper: A2aEventMapper = None
    http_kwargs: dict = {}
    handoff_message: str = None


class A2aHostedAgent(BaseChatAgent, ComponentBase[A2aHostedAgentConfig]):
    """A chat agent that interacts with remote A2A-compatible agents.

    This agent enables communication with remote agents that implement the A2A protocol.
    It handles message conversion, streaming responses, and agent handoffs.

    Args:
        agent_card (AgentCard): The agent's capabilities and metadata
        event_mapper (A2aEventMapper, optional): Custom event mapper for message conversion
        http_kwargs (dict, optional): Additional HTTP client configuration
        handoff_message (str, optional): Template for handoff messages

    Example:
        ```python
        # Create an agent card
        card = AgentCard(
            name="FoodAgent", description="A food recipe assistant", capabilities=AgentCapabilities(streaming=True)
        )

        # Initialize the agent
        agent = A2aHostedAgent(agent_card=card, event_mapper=A2aEventMapper("FoodAgent"))

        # Use in conversation
        response = await agent.on_messages(
            [TextMessage(content="Suggest a pasta recipe", source="user")], CancellationToken()
        )
        ```

    Note:
        - Supports both streaming and non-streaming responses
        - Handles multi-modal messages (text, data, images)
        - Integrates with AutoGen's message and event system
    """

    def __init__(
        self,
        agent_card: AgentCard,
        event_mapper: A2aEventMapper = None,
        http_kwargs: dict = None,
        handoff_message: str = None,
    ):
        super().__init__(name="A2aHostedAgent", description="A hosted agent for A2A operations.")
        self._default_http_kwargs = http_kwargs if http_kwargs is not None else dict()
        self._agent_card = agent_card
        self._task_id = str(uuid.uuid4())
        self._event_mapper = event_mapper if event_mapper is not None else A2aEventMapper(agent_card.name)
        self._handoff_message = (
            handoff_message
            if handoff_message is not None
            else "Transferred to {target}, adopting the role of {target} immediately."
        )

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
        """Convert AutoGen messages to A2A message format.

        This method handles the conversion of various AutoGen message types to the A2A protocol format.
        It can be overridden by subclasses for custom message formatting.

        Args:
            autogen_messages (Sequence[BaseChatMessage]): The AutoGen messages to convert

        Returns:
            MessageSendParams: The converted A2A message parameters

        Example:
            ```python
            # Text message conversion
            text_msg = TextMessage(content="Hello", source="user")
            params = agent._build_a2a_message([text_msg])

            # Multi-modal message conversion
            multi_msg = MultiModalMessage(content=["Recipe:", Image.from_file("recipe.jpg")], source="user")
            params = agent._build_a2a_message([multi_msg])
            ```

        Note:
            Supports conversion of:
            - Text messages -> TextPart
            - Images -> FilePart
            - Structured data -> DataPart
        """
        message = Message(messageId=str(uuid.uuid4()), parts=list(), role=Role.user, taskId=self._task_id)

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

        return MessageSendParams(message=message)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    def _get_latest_handoff(self, messages: Sequence[BaseChatMessage]) -> Optional[HandoffMessage]:
        """Find the most recent HandoffMessage targeting this agent.

        Searches through the message sequence in reverse order to find the last handoff
        message that targets this agent.

        Args:
            messages (Sequence[BaseChatMessage]): The sequence of messages to search

        Returns:
            Optional[HandoffMessage]: The most recent handoff message, or None if none found

        Raises:
            AssertionError: If a handoff message targets a different agent

        Example:
            ```python
            handoff = agent._get_latest_handoff(
                [
                    TextMessage(content="Hello", source="user"),
                    HandoffMessage(target="food_agent", source="user"),
                    TextMessage(content="Recipe?", source="user"),
                ]
            )
            if handoff:
                print(f"Found handoff from {handoff.source}")
            ```
        """
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
        """Process incoming messages and generate streaming responses.

        This method handles the core interaction with the remote A2A agent, supporting
        both streaming and non-streaming responses.

        Args:
            messages (Sequence[BaseChatMessage]): The messages to process
            cancellation_token (CancellationToken): Token for cancelling the operation

        Yields:
            Union[BaseAgentEvent, BaseChatMessage, Response]: Stream of responses and events

        Example:
            ```python
            messages = [TextMessage(content="Recipe for pasta?", source="user")]
            async for response in agent.on_messages_stream(messages, CancellationToken()):
                if isinstance(response, TextMessage):
                    print(response.content)
                elif isinstance(response, Response):
                    print("Final response received")
            ```

        Note:
            - Automatically detects and uses streaming if available
            - Handles handoffs between agents
            - Returns intermediate messages and final response
        """
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
            chat_message=output_messages[-1],  # Return the last message as the chat message
        )

    async def call_agent(
        self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage = None
    ) -> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Response], None]:
        """Make a non-streaming call to the remote A2A agent.

        Sends a message to the remote agent and processes its response in a single request.

        Args:
            params (MessageSendParams): The A2A message parameters
            cancellation_token (CancellationToken): Token for cancelling the operation
            handoff (HandoffMessage, optional): Handoff message if this is part of a handoff

        Yields:
            Union[BaseAgentEvent, BaseChatMessage, Response]: Agent messages and events

        Raises:
            Exception: If the A2A response contains an error
            RuntimeError: If the task fails
            AssertionError: If no agent messages are found

        Example:
            ```python
            params = MessageSendParams(message=Message(...))
            async for response in agent.call_agent(params, CancellationToken()):
                if isinstance(response, TextMessage):
                    print(f"Agent says: {response.content}")
            ```

        Note:
            - Processes the entire conversation history
            - Handles task state transitions
            - Supports agent handoffs
        """

        async with AsyncClient(**self._default_http_kwargs) as httpx_client:
            a2a_client = A2AClient(httpx_client, self._agent_card)
            response = await a2a_client.send_message(request=SendMessageRequest(id=str(uuid.uuid4()), params=params))
        if isinstance(response.root, JSONRPCErrorResponse):
            raise Exception(
                f"Error in A2A response: {response.root.error.message}",
                response.root.error.code,
                response.root.error.data,
            )

        history = response.root.result.history[get_index_of_user_message(response.root.result.history, params) + 1 :]

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
            yield HandoffMessage(
                content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source
            )  # Handoff to the last agent

        yield last_message

    async def call_agent_stream(
        self, params: MessageSendParams, cancellation_token: CancellationToken, handoff: HandoffMessage = None
    ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | Response], None]:
        """Make a streaming call to the remote A2A agent.

        Sends a message to the remote agent and processes its response as a stream of events.

        Args:
            params (MessageSendParams): The A2A message parameters
            cancellation_token (CancellationToken): Token for cancelling the operation
            handoff (HandoffMessage, optional): Handoff message if this is part of a handoff

        Yields:
            Union[BaseAgentEvent, BaseChatMessage, Response]: Stream of agent messages and events

        Raises:
            RuntimeError: If streaming is not supported or task fails
            Exception: If the A2A response contains an error
            AssertionError: If no agent messages are found

        Example:
            ```python
            params = MessageSendParams(message=Message(...))
            async for event in agent.call_agent_stream(params, CancellationToken()):
                if isinstance(event, ModelClientStreamingChunkEvent):
                    print(f"Streaming chunk: {event.content}")
                elif isinstance(event, TextMessage):
                    print(f"Final response: {event.content}")
            ```

        Note:
            - Processes real-time artifacts and status updates
            - Supports task state transitions
            - Handles streaming events and final responses
            - Manages agent handoffs
        """
        if not self._agent_card.capabilities.streaming:
            raise RuntimeError("Streaming is not supported by this agent.")
        final_state = None
        request = SendStreamingMessageRequest(id=str(uuid.uuid4()), params=params)
        last_message = None
        async with AsyncClient(**self._default_http_kwargs) as httpx_client:
            a2a_client = A2AClient(httpx_client, self._agent_card)

            async for response in a2a_client.send_message_streaming(request):
                if isinstance(response.root, JSONRPCErrorResponse):
                    raise Exception(
                        f"Error in A2A response: {response.root.error.message}",
                        response.root.error.code,
                        response.root.error.data,
                    )
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
                f"Task failed with error: {last_message.to_text() if last_message is not None else 'Unknown error'}"
            )

        if final_state == TaskState.input_required and handoff:
            yield HandoffMessage(
                content=self._handoff_message.format(handoff.source), source=self.name, target=handoff.source
            )  # Handoff to the last agent

        yield last_message

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the agent to its initial state.

        This method generates a new task ID, effectively starting a fresh conversation.

        Args:
            cancellation_token (CancellationToken): Token for cancelling the operation

        Example:
            ```python
            await agent.on_reset(CancellationToken())
            # Agent now has a new task ID for the next conversation
            ```
        """
        self._task_id = str(uuid.uuid4())

    async def save_state(self) -> Mapping[str, Any]:
        return A2aHostedAgentState(task_id=self._task_id).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore agent from saved state."""
        config = A2aHostedAgentState.model_validate(state)
        self._task_id = config.task_id or str(uuid.uuid4())

    def _to_config(self) -> A2aHostedAgentConfig:
        return A2aHostedAgentConfig(
            agent_card=self._agent_card,
            event_mapper=self._event_mapper,
            http_kwargs=self._default_http_kwargs,
            handoff_message=self._handoff_message,
        )

    @classmethod
    def _from_config(cls, config: A2aHostedAgentConfig) -> Self:
        return cls(
            agent_card=config.agent_card,
            event_mapper=config.event_mapper or A2aEventMapper(config.agentCard),
            http_kwargs=config.http_kwargs or {},
            handoff_message=config.handoff_message
            or "Transferred to {target}, adopting the role of {target} immediately.",
        )
