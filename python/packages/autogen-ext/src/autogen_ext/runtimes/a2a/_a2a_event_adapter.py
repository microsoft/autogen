import json
import uuid
from abc import ABC, abstractmethod
from typing import Union

from a2a.types import TaskState, TextPart, Part, FilePart, FileWithBytes, DataPart, \
    TaskArtifactUpdateEvent, Artifact
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage, MultiModalMessage, \
    StructuredMessage, ModelClientStreamingChunkEvent
from autogen_core import Image
from pydantic import BaseModel

from _a2a_execution_context import A2aExecutionContext


class A2aEventAdapter(ABC, BaseModel):

    @abstractmethod
    def handle_events(self, message: Union[BaseAgentEvent, BaseChatMessage], context: A2aExecutionContext):
        """Handle events from the agent."""
        pass

class BaseA2aEventAdapter(A2aEventAdapter):

    def handle_events(self, message: Union[BaseAgentEvent, BaseChatMessage], context: A2aExecutionContext):
        """Handler for agent events."""
        if isinstance(message, BaseChatMessage) and message.source == context.user_proxy_agent.name:
            # This is a user message, we can ignore it in the context of task updates
            return
        if isinstance(message, TextMessage):
            text = message.to_text()
            context.updater.update_status(state=TaskState.working,
                                  message=context.updater.new_agent_message([Part(root=TextPart(text=text))], metadata= message.metadata or None))
        if isinstance(message, MultiModalMessage):
            parts = []
            for content in message.content:
                if isinstance(content, Image):
                    parts.append(Part(root=FilePart(file=FileWithBytes(bytes=content.to_base64()))))
                elif isinstance(content, str):
                    parts.append(Part(root=TextPart(text=content)))
                else:
                    raise AssertionError("Multimodal message content must be an Image or a string.")
            context.updater.update_status(state=TaskState.working,
                message=context.updater.new_agent_message(parts=parts,metadata=message.metadata))

        if isinstance(message, StructuredMessage):
            data_part = DataPart(data=json.loads(str(message.to_model_message().content)))
            context.updater.update_status(state=TaskState.working,
                                  message=context.updater.new_agent_message(parts=[Part(root=data_part)],
                                                                    metadata=message.metadata))
        if isinstance(message, ModelClientStreamingChunkEvent):
            if not context.streaming_chunks_id:
                context.streaming_chunks_id = str(uuid.uuid4())

            context.updater.event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    taskId=context.updater.task_id,
                    contextId=context.updater.context_id,
                    append=True,
                    artifact=Artifact(
                        artifactId=context.streaming_chunks_id,
                        parts=[Part(root=TextPart(text=message.to_text()))],
                        metadata=message.metadata or None,
                    ),
                )
            )
        else:
            if context.streaming_chunks_id:
                context.updater.event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        taskId=context.updater.task_id,
                        contextId=context.updater.context_id,
                        lastChunk= True,
                        append= True,
                        artifact=Artifact(
                            artifactId=context.streaming_chunks_id,
                            parts=[],
                            metadata=None,
                        ),
                    )
                )
                context.streaming_chunks_id = None