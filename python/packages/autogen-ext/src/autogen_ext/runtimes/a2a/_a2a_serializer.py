import json
import uuid
from typing import Union

from a2a.server.tasks import TaskUpdater
from a2a.types import Role, TaskState, TextPart, Part, FilePart, FileWithBytes, FileWithUri, DataPart, \
    TaskArtifactUpdateEvent, Artifact
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage, MultiModalMessage, \
    StructuredMessage, ModelClientStreamingChunkEvent
from autogen_core import Image

from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent


class A2aSerializer:

    def __init__(self, updater: TaskUpdater, user_proxy_agent: A2aExternalUserProxyAgent):
        self.updater = updater
        self.user_proxy_agent = user_proxy_agent
        self.streaming_chunks_id = None

    def handle_events(self, message: Union[BaseAgentEvent, BaseChatMessage]):
        """Handler for agent events."""
        if isinstance(message, BaseChatMessage) and message.source == self.user_proxy_agent.name:
            # This is a user message, we can ignore it in the context of task updates
            return
        if isinstance(message, TextMessage):
            text = message.to_text()
            self.updater.update_status(state=TaskState.working,
                                  message=self.updater.new_agent_message([Part(root=TextPart(text=text))], metadata= message.metadata or None))
        if isinstance(message, MultiModalMessage):
            parts = []
            for content in message.content:
                if isinstance(content, Image):
                    parts.append(Part(root=FilePart(file=FileWithBytes(bytes=content.to_base64()))))
                elif isinstance(content, str):
                    parts.append(Part(root=TextPart(text=content)))
                else:
                    raise AssertionError("Multimodal message content must be an Image or a string.")
            self.updater.update_status(state=TaskState.working,
                message=self.updater.new_agent_message(parts=parts,metadata=message.metadata))

        if isinstance(message, StructuredMessage):
            data_part = DataPart(data=json.loads(str(message.to_model_message().content)))
            self.updater.update_status(state=TaskState.working,
                                  message=self.updater.new_agent_message(parts=[Part(root=data_part)],
                                                                    metadata=message.metadata))
        if isinstance(message, ModelClientStreamingChunkEvent):
            if not self.streaming_chunks_id:
                self.streaming_chunks_id = str(uuid.uuid4())

            self.updater.event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    taskId=self.updater.task_id,
                    contextId=self.updater.context_id,
                    append=True,
                    artifact=Artifact(
                        artifactId=self.streaming_chunks_id,
                        parts=[Part(root=TextPart(text=message.to_text()))],
                        metadata=message.metadata or None,
                    ),
                )
            )
        else:
            if self.streaming_chunks_id:
                self.updater.event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        taskId=self.updater.task_id,
                        contextId=self.updater.context_id,
                        lastChunk= True,
                        append= True,
                        artifact=Artifact(
                            artifactId=self.streaming_chunks_id,
                            parts=[],
                            metadata=None,
                        ),
                    )
                )
                self.streaming_chunks_id = None