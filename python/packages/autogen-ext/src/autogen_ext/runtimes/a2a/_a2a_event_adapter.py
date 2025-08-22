import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Coroutine, Union

from a2a.types import Artifact, DataPart, FilePart, FileWithBytes, Part, TaskArtifactUpdateEvent, TaskState, TextPart
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StructuredMessage,
    TextMessage,
)
from autogen_core import Image
from pydantic import BaseModel

from ._a2a_execution_context import A2aExecutionContext


class A2aEventAdapter(ABC, BaseModel):
    """Abstract base class for adapting AutoGen events to A2A protocol events.

    This class defines the interface for converting AutoGen chat messages and events
    into A2A protocol compatible events. Implementers should handle different types
    of AutoGen messages and translate them into appropriate A2A task updates and events.

    Example:
        ```python
        class CustomEventAdapter(A2aEventAdapter):
            def handle_events(self, message, context):
                if isinstance(message, TextMessage):
                    context.updater.update_status(
                        state=TaskState.working,
                        message=context.updater.new_agent_message([Part(root=TextPart(text=message.content))]),
                    )
        ```
    """

    @abstractmethod
    async def handle_events(
        self, message: Union[BaseAgentEvent, BaseChatMessage], context: A2aExecutionContext
    ) -> None:
        """Handle AutoGen events and convert them to A2A protocol events.

        Args:
            message (Union[BaseAgentEvent, BaseChatMessage]): The AutoGen message or event
            context (A2aExecutionContext): The execution context containing task updater

        This method should be implemented to handle different types of AutoGen messages:
        - TextMessage -> A2A text parts
        - MultiModalMessage -> A2A file and text parts
        - StructuredMessage -> A2A data parts
        - ModelClientStreamingChunkEvent -> A2A streaming artifacts
        """
        pass


class BaseA2aEventAdapter(A2aEventAdapter):
    """Base implementation of A2aEventAdapter with standard event handling.

    This class provides a default implementation for converting AutoGen events to A2A
    protocol events. It handles text messages, multi-modal content, structured data,
    and streaming events.

    The adapter manages:
    - Text message conversion
    - Image and file handling
    - Structured data serialization
    - Streaming chunk management
    - Task state updates

    Example:
        ```python
        adapter = BaseA2aEventAdapter()
        context = A2aExecutionContext(...)

        # Handle a text message
        adapter.handle_events(TextMessage(content="Processing request...", source="assistant"), context)

        # Handle a multi-modal message with image
        adapter.handle_events(MultiModalMessage(content=["Result:", image_data], source="assistant"), context)
        ```
    """

    async def handle_events(
        self, message: Union[BaseAgentEvent, BaseChatMessage], context: A2aExecutionContext
    ) -> None:
        """Process AutoGen events and update A2A task state.

        This implementation handles various types of AutoGen messages and converts
        them into appropriate A2A protocol updates.

        Args:
            message (Union[BaseAgentEvent, BaseChatMessage]): The message to process
            context (A2aExecutionContext): The execution context

        Raises:
            AssertionError: If multi-modal content is neither Image nor string

        Note:
            - Ignores messages from the user proxy agent
            - Updates task state to 'working' for agent messages
            - Manages streaming chunks with unique IDs
            - Handles proper closure of streaming events
        """
        if isinstance(message, BaseChatMessage) and message.source == context.user_proxy_agent.name:
            # This is a user message, we can ignore it in the context of task updates
            return
        if isinstance(message, TextMessage):
            text = message.to_text()
            await context.updater.update_status(
                state=TaskState.working,
                message=context.updater.new_agent_message(
                    [Part(root=TextPart(text=text))], metadata=message.metadata or None
                ),
            )
        if isinstance(message, MultiModalMessage):
            parts = []
            for content in message.content:
                if isinstance(content, Image):
                    parts.append(Part(root=FilePart(file=FileWithBytes(bytes=content.to_base64()))))
                elif isinstance(content, str):
                    parts.append(Part(root=TextPart(text=content)))
                else:
                    raise AssertionError("Multimodal message content must be an Image or a string.")
            await context.updater.update_status(
                state=TaskState.working,
                message=context.updater.new_agent_message(parts=parts, metadata=message.metadata),
            )

        if isinstance(message, StructuredMessage):
            data_part = DataPart(data=json.loads(str(message.to_model_message().content)))
            await context.updater.update_status(
                state=TaskState.working,
                message=context.updater.new_agent_message(parts=[Part(root=data_part)], metadata=message.metadata),
            )
        if isinstance(message, ModelClientStreamingChunkEvent):
            if not context.streaming_chunks_id:
                context.streaming_chunks_id = str(uuid.uuid4())

            await context.updater.event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=context.updater.task_id,
                    context_id=context.updater.context_id,
                    append=True,
                    artifact=Artifact(
                        artifact_id=context.streaming_chunks_id,
                        parts=[Part(root=TextPart(text=message.to_text()))],
                        metadata=message.metadata or None,
                    ),
                )
            )
        else:
            if context.streaming_chunks_id:
                await context.updater.event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        task_id=context.updater.task_id,
                        context_id=context.updater.context_id,
                        last_chunk=True,
                        append=True,
                        artifact=Artifact(
                            artifact_id=context.streaming_chunks_id,
                            parts=[],
                            metadata=None,
                        ),
                    )
                )
                context.streaming_chunks_id = None
