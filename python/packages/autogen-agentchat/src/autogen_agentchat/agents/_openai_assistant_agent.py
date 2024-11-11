import asyncio
import os
from typing import Callable, List, Optional, Sequence

import aiofiles
from autogen_core.base import CancellationToken
from autogen_agentchat.messages import ChatMessage, TextMessage
from openai import AsyncAssistantEventHandler, AsyncClient
from openai.types.beta.thread import ToolResources, ToolResourcesFileSearch
from openai.types.beta.threads import Message, Text, TextDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from typing_extensions import override

from ._base_chat_agent import BaseChatAgent


class OpenAIAssistantChatAgent(BaseChatAgent):
    """An agent implementation that uses the OpenAI Assistant API to generate responses."""

    def __init__(
        self,
        name: str,
        description: str,
        client: AsyncClient,
        model: str,
        instructions: str,
        tools: Optional[List[dict]] = None,
    ) -> None:
        super().__init__(name, description)
        if tools is None:
            tools = []
        self._client = client
        self._assistant = None
        self._thread = None
        self._model = model
        self._instructions = instructions
        self._tools = tools

    async def _ensure_initialized(self):
        """Ensure assistant and thread are created."""
        if self._assistant is None:
            self._assistant = await self._client.beta.assistants.create(
                model=self._model,
                description=self.description,
                instructions=self._instructions,
                tools=self._tools,
            )
        
        if self._thread is None:
            self._thread = await self._client.beta.threads.create()

    @property
    def _assistant_id(self) -> str:
        if self._assistant is None:
            raise ValueError("Assistant not initialized")
        return self._assistant.id

    @property 
    def _thread_id(self) -> str:
        if self._thread is None:
            raise ValueError("Thread not initialized")
        return self._thread.id

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        """Handle incoming messages and return a response message."""
        await self._ensure_initialized()

        for message in messages:
            content = message.content.strip().lower()
            if content == "reset":
                await self.on_reset(cancellation_token)
            elif content.startswith("upload_code "):
                file_path = message.content[len("upload_code ") :].strip()
                await self.on_upload_for_code_interpreter(file_path, cancellation_token)
            elif content.startswith("upload_search "):
                file_path = message.content[len("upload_search ") :].strip()
                await self.on_upload_for_file_search(file_path, cancellation_token)
            else:
                await self.handle_text_message(message.content, cancellation_token)

        # Create and start a run
        run = await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.runs.create(
                    thread_id=self._thread_id,
                    assistant_id=self._assistant_id,
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

        # Get messages after run completion
        messages = await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.messages.list(
                    thread_id=self._thread_id,
                    order="desc",
                    limit=1
                )
            )
        )

        if not messages.data:
            raise ValueError("No messages received from assistant")

        # Get the last message's content
        last_message = messages.data[0]
        if not last_message.content:
            raise ValueError(f"No content in the last message: {last_message}")

        # Extract text content
        text_content = [content for content in last_message.content if content.type == "text"]
        if not text_content:
            raise ValueError(f"Expected text content in the last message: {last_message.content}")

        # Return the assistant's response as a ChatMessage
        return TextMessage(source=self.name, content=text_content[0].text.value)

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

    async def on_reset(self, cancellation_token: CancellationToken):
        """Handle reset command by deleting all messages in the thread."""
        # Retrieve all message IDs in the thread
        all_msgs = []
        after = None
        while True:
            msgs = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.beta.threads.messages.list(self._thread_id, after=after))
            )
            for msg in msgs.data:
                all_msgs.append(msg.id)
                after = msg.id
            if not msgs.has_next_page():
                break

        # Delete all messages
        for msg_id in all_msgs:
            status = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.messages.delete(message_id=msg_id, thread_id=self._thread_id)
                )
            )
            assert status.deleted is True

    async def on_upload_for_code_interpreter(self, file_path: str, cancellation_token: CancellationToken):
        """Handle file uploads for the code interpreter."""
        # Read the file content
        async with aiofiles.open(file_path, mode="rb") as f:
            file_content = await cancellation_token.link_future(asyncio.ensure_future(f.read()))
        file_name = os.path.basename(file_path)

        # Upload the file
        file = await cancellation_token.link_future(
            asyncio.ensure_future(self._client.files.create(file=(file_name, file_content), purpose="assistants"))
        )

        # Update thread with the new file
        thread = await cancellation_token.link_future(
            asyncio.ensure_future(self._client.beta.threads.retrieve(thread_id=self._thread_id))
        )
        tool_resources: ToolResources = thread.tool_resources or ToolResources()
        code_interpreter = tool_resources.code_interpreter or ToolResourcesFileSearch()
        file_ids = code_interpreter.file_ids or []
        file_ids.append(file.id)
        tool_resources.code_interpreter = ToolResourcesFileSearch(file_ids=file_ids)

        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.threads.update(
                    thread_id=self._thread_id,
                    tool_resources=tool_resources,
                )
            )
        )

    async def on_upload_for_file_search(self, file_path: str, cancellation_token: CancellationToken):
        """Handle file uploads for file search."""
        # Read the file content
        async with aiofiles.open(file_path, mode="rb") as f:
            file_content = await cancellation_token.link_future(asyncio.ensure_future(f.read()))
        file_name = os.path.basename(file_path)

        # Upload the file to the vector store
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=self._vector_store_id,
                    files=[(file_name, file_content)],
                )
            )
        )
