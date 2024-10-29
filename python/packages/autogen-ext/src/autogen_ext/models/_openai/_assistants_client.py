# packages/autogen-ext/src/autogen_ext/models/_openai/_openai_assistant_client.py

import asyncio
import logging
import os
from typing import Any, AsyncIterable, Callable, Dict, List, Mapping, Optional, Sequence, Union

import aiofiles
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import CancellationToken
from autogen_core.components import Image
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tools import Tool, ToolSchema
from openai import AsyncAssistantEventHandler, AsyncClient
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import ToolResources
from openai.types.beta.threads import (
    ImageFileContent,
    MessageContent,
    TextContent,
)
from openai.types.beta.threads import Message as OAIMessage
from openai.types.beta.threads.runs import (
    Run as OAIRun,
)
from openai.types.beta.threads.runs import (
    RunEvent,
    RunEventText,
)
from pydantic import BaseModel

logger = logging.getLogger(EVENT_LOGGER_NAME)


# Helper functions to convert between autogen and OpenAI message types
def llm_message_to_oai_content(message: LLMMessage) -> List[MessageContent]:
    contents = []
    if isinstance(message, UserMessage):
        if isinstance(message.content, str):
            contents.append(TextContent(type="text", text={"value": message.content}))
        elif isinstance(message.content, list):
            for part in message.content:
                if isinstance(part, str):
                    contents.append(TextContent(type="text", text={"value": part}))
                elif isinstance(part, Image):
                    # Convert Image to ImageFileContent
                    contents.append(
                        ImageFileContent(
                            type="image_file",
                            image_file={"file_id": part.data_uri},  # Assuming data_uri contains file_id
                        )
                    )
                else:
                    raise ValueError(f"Unsupported content type: {type(part)}")
        else:
            raise ValueError(f"Unsupported content type: {type(message.content)}")
    elif isinstance(message, SystemMessage):
        # System messages can be added as assistant messages with role 'system'
        contents.append(TextContent(type="text", text={"value": message.content}))
    elif isinstance(message, AssistantMessage):
        if isinstance(message.content, str):
            contents.append(TextContent(type="text", text={"value": message.content}))
        elif isinstance(message.content, list):
            # Handle function calls if needed
            contents.append(TextContent(type="text", text={"value": str(message.content)}))
        else:
            raise ValueError(f"Unsupported assistant content type: {type(message.content)}")
    else:
        raise ValueError(f"Unsupported message type: {type(message)}")
    return contents


class BaseOpenAIAssistantClient(ChatCompletionClient):
    def __init__(
        self,
        client: AsyncClient,
        assistant_id: str,
        thread_id: Optional[str] = None,
        model_capabilities: Optional[ModelCapabilities] = None,
    ):
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id  # If None, a new thread will be created
        self._model_capabilities = model_capabilities or ModelCapabilities(
            function_calling=True,
            vision=False,
            json_output=True,
        )
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._assistant: Optional[Assistant] = None

    async def _ensure_thread(self) -> str:
        if self._thread_id is None:
            thread = await self._client.beta.threads.create()
            self._thread_id = thread.id
        return self._thread_id

    async def reset_thread(self, cancellation_token: Optional[CancellationToken] = None):
        """Reset the thread by deleting all messages in the thread."""
        thread_id = await self._ensure_thread()
        all_msgs: List[str] = []
        while True:
            if not all_msgs:
                list_future = asyncio.ensure_future(self._client.beta.threads.messages.list(thread_id=thread_id))
            else:
                list_future = asyncio.ensure_future(
                    self._client.beta.threads.messages.list(thread_id=thread_id, after=all_msgs[-1])
                )
            if cancellation_token:
                cancellation_token.link_future(list_future)
            msgs = await list_future
            all_msgs.extend(msg.id for msg in msgs.data)
            if not msgs.has_next_page():
                break
        for msg_id in all_msgs:
            delete_future = asyncio.ensure_future(
                self._client.beta.threads.messages.delete(thread_id=thread_id, message_id=msg_id)
            )
            if cancellation_token:
                cancellation_token.link_future(delete_future)
            await delete_future

    async def upload_file_to_code_interpreter(
        self, file_path: str, cancellation_token: Optional[CancellationToken] = None
    ):
        """Upload a file to the code interpreter and update the thread."""
        thread_id = await self._ensure_thread()
        # Get the file content
        async with aiofiles.open(file_path, mode="rb") as f:
            read_future = asyncio.ensure_future(f.read())
            if cancellation_token:
                cancellation_token.link_future(read_future)
            file_content = await read_future
        file_name = os.path.basename(file_path)
        # Upload the file
        file_future = asyncio.ensure_future(
            self._client.files.create(file=(file_name, file_content), purpose="assistants")
        )
        if cancellation_token:
            cancellation_token.link_future(file_future)
        file = await file_future
        # Get existing file ids from tool resources
        retrieve_future = asyncio.ensure_future(self._client.beta.threads.retrieve(thread_id=thread_id))
        if cancellation_token:
            cancellation_token.link_future(retrieve_future)
        thread = await retrieve_future
        tool_resources: ToolResources = thread.tool_resources if thread.tool_resources else ToolResources()
        if tool_resources.code_interpreter and tool_resources.code_interpreter.file_ids:
            file_ids = tool_resources.code_interpreter.file_ids + [file.id]
        else:
            file_ids = [file.id]
        # Update thread with new file
        update_future = asyncio.ensure_future(
            self._client.beta.threads.update(
                thread_id=thread_id,
                tool_resources={
                    "code_interpreter": {"file_ids": file_ids},
                },
            )
        )
        if cancellation_token:
            cancellation_token.link_future(update_future)
        await update_future

    async def upload_file_to_vector_store(
        self, file_path: str, vector_store_id: str, cancellation_token: Optional[CancellationToken] = None
    ):
        """Upload a file to the vector store."""
        # Get the file content
        async with aiofiles.open(file_path, mode="rb") as f:
            read_future = asyncio.ensure_future(f.read())
            if cancellation_token:
                cancellation_token.link_future(read_future)
            file_content = await read_future
        file_name = os.path.basename(file_path)
        # Upload the file
        upload_future = asyncio.ensure_future(
            self._client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store_id,
                files=[(file_name, file_content)],
            )
        )
        if cancellation_token:
            cancellation_token.link_future(upload_future)
        await upload_future

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        thread_id = await self._ensure_thread()
        # Send messages to the thread
        for message in messages:
            contents = llm_message_to_oai_content(message)
            await self._client.beta.threads.messages.create(
                thread_id=thread_id,
                content=contents,
                role=message.__class__.__name__.lower(),  # 'user', 'assistant', etc.
                metadata={"sender": message.source} if hasattr(message, "source") else {},
            )
        # Run the assistant
        run_future = asyncio.ensure_future(
            self._client.beta.threads.create_and_run(
                assistant_id=self._assistant_id,
                thread={"id": thread_id},
            )
        )
        if cancellation_token is not None:
            cancellation_token.link_future(run_future)
        _: OAIRun = await run_future
        # Get the last message
        messages_result = await self._client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)
        last_message = messages_result.data[0]
        # Extract content
        content = ""
        for part in last_message.content:
            if part.type == "text":
                content += part.text.value
            # Handle other content types if necessary
        # Create usage data (Note: OpenAI Assistant API might not provide token usage directly)
        usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        result = CreateResult(
            finish_reason="stop",
            content=content,
            usage=usage,
            cached=False,
        )
        return result

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        assistant_event_handler_factory: Optional[Callable[[], AsyncAssistantEventHandler]] = None,
    ) -> AsyncIterable[Union[str, CreateResult]]:
        thread_id = await self._ensure_thread()
        # Send messages to the thread
        for message in messages:
            contents = llm_message_to_oai_content(message)
            await self._client.beta.threads.messages.create(
                thread_id=thread_id,
                content=contents,
                role=message.__class__.__name__.lower(),
                metadata={"sender": message.source} if hasattr(message, "source") else {},
            )
        # Run the assistant with streaming
        if assistant_event_handler_factory:
            event_handler = assistant_event_handler_factory()
        else:
            event_handler = AsyncAssistantEventHandler()  # default handler
        stream_manager = self._client.beta.threads.create_and_run_stream(
            assistant_id=self._assistant_id,
            thread={"id": thread_id},
            event_handler=event_handler,
        )
        stream = stream_manager.stream()
        if cancellation_token is not None:
            cancellation_token.link_future(asyncio.ensure_future(stream_manager.wait_until_done()))
        content = ""
        async for event in stream:
            if isinstance(event, RunEventText):
                content += event.text.value
                yield event.text.value
            # Handle other event types if necessary
        # After the stream is done, create the final result
        usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        result = CreateResult(
            finish_reason="stop",
            content=content,
            usage=usage,
            cached=False,
        )
        yield result

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        # Implement token counting logic if possible
        raise NotImplementedError("Token counting is not supported for OpenAI Assistant API Client")

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        # Implement remaining tokens logic if possible
        raise NotImplementedError("Remaining tokens are not supported for OpenAI Assistant API Client")

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._model_capabilities


class OpenAIAssistantClient(BaseOpenAIAssistantClient):
    def __init__(
        self,
        client: AsyncClient,
        assistant_id: str,
        thread_id: Optional[str] = None,
        model_capabilities: Optional[ModelCapabilities] = None,
    ):
        super().__init__(client, assistant_id, thread_id, model_capabilities)

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        client = AsyncClient(**config.get("client_kwargs", {}))
        assistant_id = config["assistant_id"]
        thread_id = config.get("thread_id")
        model_capabilities = config.get("model_capabilities")
        return cls(client, assistant_id, thread_id, model_capabilities)
