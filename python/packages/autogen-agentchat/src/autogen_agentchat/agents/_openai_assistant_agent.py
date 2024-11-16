import asyncio
import logging
import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, cast

import aiofiles
from autogen_core.base import CancellationToken
from autogen_core.components.tools import Tool
from openai import NOT_GIVEN, AsyncClient, NotGiven
from openai.pagination import AsyncCursorPage
from openai.types import FileObject
from openai.types.beta import thread_update_params
from openai.types.beta.assistant import Assistant
from openai.types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam
from openai.types.beta.assistant_tool_param import AssistantToolParam
from openai.types.beta.function_tool_param import FunctionToolParam
from openai.types.beta.thread import Thread, ToolResources, ToolResourcesCodeInterpreter
from openai.types.beta.threads import Message, MessageDeleted, Run
from openai.types.beta.vector_store import VectorStore
from openai.types.shared_params.function_definition import FunctionDefinition

from autogen_agentchat.messages import ChatMessage, HandoffMessage, MultiModalMessage, StopMessage, TextMessage

from .. import EVENT_LOGGER_NAME
from ..base import Response
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


def _convert_tool_to_function_param(tool: Tool) -> FunctionToolParam:
    """Convert an autogen Tool to an OpenAI Assistant function tool parameter."""
    schema = tool.schema
    parameters: Dict[str, object] = {}
    if "parameters" in schema:
        parameters = {
            "type": schema["parameters"]["type"],
            "properties": schema["parameters"]["properties"],
        }
        if "required" in schema["parameters"]:
            parameters["required"] = schema["parameters"]["required"]

    function_def = FunctionDefinition(
        name=schema["name"],
        description=schema.get("description", ""),
        parameters=parameters,
    )
    return FunctionToolParam(type="function", function=function_def)


class OpenAIAssistantAgent(BaseChatAgent):
    """An agent implementation that uses the OpenAI Assistant API to generate responses."""

    def __init__(
        self,
        name: str,
        description: str,
        client: AsyncClient,
        model: str,
        instructions: str,
        tools: Optional[Iterable[AssistantToolParam | Tool]] = None,
        assistant_id: Optional[str] = None,
        metadata: Optional[object] = None,
        response_format: Optional[AssistantResponseFormatOptionParam] = None,
        temperature: Optional[float] = None,
        tool_resources: Optional[ToolResources] = None,
        top_p: Optional[float] = None,
    ) -> None:
        super().__init__(name, description)
        if tools is None:
            tools = []

        # Convert autogen Tools to OpenAI Assistant tools
        converted_tools: List[AssistantToolParam] = []
        for tool in tools:
            if isinstance(tool, Tool):
                converted_tools.append(_convert_tool_to_function_param(tool))
            else:
                converted_tools.append(tool)

        self._client = client
        self._assistant: Optional[Assistant] = None
        self._thread: Optional[Thread] = None
        self._model = model
        self._instructions = instructions
        self._tools = converted_tools
        self._assistant_id = assistant_id
        self._metadata = metadata
        self._response_format = response_format
        self._temperature = temperature
        self._tool_resources = tool_resources
        self._top_p = top_p
        self._vector_store_id: Optional[str] = None
        self._uploaded_file_ids: List[str] = []

    async def _ensure_initialized(self) -> None:
        """Ensure assistant and thread are created."""
        if self._assistant is None:
            if self._assistant_id:
                self._assistant = await self._client.beta.assistants.retrieve(assistant_id=self._assistant_id)
            else:
                self._assistant = await self._client.beta.assistants.create(
                    model=self._model,
                    description=self.description,
                    instructions=self._instructions,
                    tools=self._tools,
                    metadata=self._metadata,
                    response_format=self._response_format if self._response_format else NOT_GIVEN,  # type: ignore
                    temperature=self._temperature,
                    tool_resources=self._tool_resources if self._tool_resources else NOT_GIVEN,  # type: ignore
                    top_p=self._top_p,
                )

        if self._thread is None:
            self._thread = await self._client.beta.threads.create()

    @property
    def _get_assistant_id(self) -> str:
        if self._assistant is None:
            raise ValueError("Assistant not initialized")
        return self._assistant.id

    @property
    def _thread_id(self) -> str:
        if self._thread is None:
            raise ValueError("Thread not initialized")
        return self._thread.id

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handle incoming messages and return a response."""
        await self._ensure_initialized()

        # Process all messages in sequence
        for message in messages:
            if isinstance(message, (TextMessage, MultiModalMessage)):
                await self.handle_text_message(str(message.content), cancellation_token)
            elif isinstance(message, (StopMessage, HandoffMessage)):
                await self.handle_text_message(message.content, cancellation_token)

        # Create and start a run
        run: Run = await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.runs.create(
                    thread_id=self._thread_id,
                    assistant_id=self._get_assistant_id,
                )
            )
        )

        # Wait for run completion by polling
        while run.status == "queued" or run.status == "in_progress":
            run = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.runs.retrieve(
                        thread_id=self._thread_id,
                        run_id=run.id,
                    )
                )
            )
            await asyncio.sleep(0.5)

        if run.status == "failed":
            raise ValueError(f"Run failed: {run.last_error}")

        # Get messages after run completion
        assistant_messages: AsyncCursorPage[Message] = await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.list(thread_id=self._thread_id, order="desc", limit=1)
            )
        )

        if not assistant_messages.data:
            raise ValueError("No messages received from assistant")

        # Get the last message's content
        last_message = assistant_messages.data[0]
        if not last_message.content:
            raise ValueError(f"No content in the last message: {last_message}")

        # Extract text content
        text_content = [content for content in last_message.content if content.type == "text"]
        if not text_content:
            raise ValueError(f"Expected text content in the last message: {last_message.content}")

        # Return the assistant's response as a Response
        chat_message = TextMessage(source=self.name, content=text_content[0].text.value)
        return Response(chat_message=chat_message)

    async def handle_text_message(self, content: str, cancellation_token: CancellationToken) -> None:
        """Handle regular text messages by adding them to the thread."""
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.create(
                    thread_id=self._thread_id,
                    content=content,
                    role="user",
                )
            )
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Handle reset command by deleting all messages in the thread."""
        # Retrieve all message IDs in the thread
        all_msgs: List[str] = []
        after: str | NotGiven = NOT_GIVEN
        while True:
            msgs: AsyncCursorPage[Message] = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.beta.threads.messages.list(self._thread_id, after=after))
            )
            for msg in msgs.data:
                all_msgs.append(msg.id)
                after = msg.id
            if not msgs.has_next_page():
                break

        # Delete all messages
        for msg_id in all_msgs:
            status: MessageDeleted = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.messages.delete(message_id=msg_id, thread_id=self._thread_id)
                )
            )
            assert status.deleted is True

    async def on_upload_for_code_interpreter(
        self, file_paths: str | Iterable[str], cancellation_token: CancellationToken
    ) -> None:
        """Handle file uploads for the code interpreter."""
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        file_ids: List[str] = []
        for file_path in file_paths:
            # Read the file content
            async with aiofiles.open(file_path, mode="rb") as f:
                file_content = await cancellation_token.link_future(asyncio.ensure_future(f.read()))
            file_name = os.path.basename(file_path)

            # Upload the file
            file: FileObject = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.files.create(file=(file_name, file_content), purpose="assistants"))
            )
            file_ids.append(file.id)
            self._uploaded_file_ids.append(file.id)

        # Update thread with the new files
        thread = await cancellation_token.link_future(
            asyncio.ensure_future(self._client.beta.threads.retrieve(thread_id=self._thread_id))
        )
        tool_resources: ToolResources = thread.tool_resources or ToolResources()
        code_interpreter: ToolResourcesCodeInterpreter = (
            tool_resources.code_interpreter or ToolResourcesCodeInterpreter()
        )
        existing_file_ids: List[str] = code_interpreter.file_ids or []
        existing_file_ids.extend(file_ids)
        tool_resources.code_interpreter = ToolResourcesCodeInterpreter(file_ids=existing_file_ids)

        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.update(
                    thread_id=self._thread_id,
                    tool_resources=cast(thread_update_params.ToolResources, tool_resources.model_dump()),
                )
            )
        )

    async def on_upload_for_file_search(
        self, file_paths: str | Iterable[str], cancellation_token: CancellationToken
    ) -> None:
        """Handle file uploads for file search."""
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        await self._ensure_initialized()

        # Check if file_search is enabled in tools
        if not any(tool.get("type") == "file_search" for tool in self._tools):
            raise ValueError(
                "File search is not enabled for this assistant. Add a file_search tool when creating the assistant."
            )

        # Create vector store if not already created
        if self._vector_store_id is None:
            vector_store: VectorStore = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.beta.vector_stores.create())
            )
            self._vector_store_id = vector_store.id

            # Update assistant with vector store ID
            await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.assistants.update(
                        assistant_id=self._get_assistant_id,
                        tool_resources={"file_search": {"vector_store_ids": [self._vector_store_id]}},
                    )
                )
            )

        # Read and prepare all files
        files_to_upload: List[Tuple[str, bytes]] = []
        for file_path in file_paths:
            async with aiofiles.open(file_path, mode="rb") as f:
                file_content = await cancellation_token.link_future(asyncio.ensure_future(f.read()))
            file_name = os.path.basename(file_path)
            files_to_upload.append((file_name, file_content))

        # Upload all files to the vector store
        batch = await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=self._vector_store_id,
                    files=files_to_upload,
                )
            )
        )
        # Store file IDs from the batch
        if batch.file_ids:
            self._uploaded_file_ids.extend(batch.file_ids)

    async def delete_uploaded_files(self, cancellation_token: CancellationToken) -> None:
        """Delete all files that were uploaded by this agent instance."""
        for file_id in self._uploaded_file_ids:
            try:
                await cancellation_token.link_future(asyncio.ensure_future(self._client.files.delete(file_id=file_id)))
            except Exception as e:
                event_logger.error(f"Failed to delete file {file_id}: {str(e)}")
        self._uploaded_file_ids = []

    async def delete_assistant(self, cancellation_token: CancellationToken) -> None:
        """Delete the assistant if it was created by this instance."""
        if self._assistant is not None and not self._assistant_id:
            try:
                await cancellation_token.link_future(
                    asyncio.ensure_future(self._client.beta.assistants.delete(assistant_id=self._get_assistant_id))
                )
                self._assistant = None
            except Exception as e:
                event_logger.error(f"Failed to delete assistant: {str(e)}")
