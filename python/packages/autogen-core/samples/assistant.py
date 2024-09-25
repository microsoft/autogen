"""This is an example of a terminal-based ChatGPT clone
using an OpenAIAssistantAgent and event-based orchestration."""

import argparse
import asyncio
import logging
import os
import re
from typing import List

import aiofiles
import openai
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext, AgentRuntime, MessageContext
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components.model_context import BufferedChatCompletionContext
from common.agents import OpenAIAssistantAgent
from common.patterns._group_chat_manager import GroupChatManager
from common.types import PublishNow, TextMessage
from openai import AsyncAssistantEventHandler
from openai.types.beta.thread import ToolResources
from openai.types.beta.threads import Message, Text, TextDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from typing_extensions import override

sep = "-" * 50


class UserProxyAgent(RoutedAgent):
    def __init__(  # type: ignore
        self,
        client: openai.AsyncClient,  # type: ignore
        assistant_id: str,
        thread_id: str,
        vector_store_id: str,
    ) -> None:  # type: ignore
        super().__init__(
            description="A human user",
        )  # type: ignore
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._vector_store_id = vector_store_id

    @message_handler()  # type: ignore
    async def on_text_message(self, message: TextMessage, ctx: MessageContext) -> None:
        # TODO: render image if message has image.
        # print(f"{message.source}: {message.content}")
        pass

    async def _get_user_input(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    @message_handler()  # type: ignore
    async def on_publish_now(self, message: PublishNow, ctx: MessageContext) -> None:
        while True:
            user_input = await self._get_user_input(f"\n{sep}\nYou: ")
            # Parse upload file command '[upload code_interpreter | file_search filename]'.
            match = re.search(r"\[upload\s+(code_interpreter|file_search)\s+(.+)\]", user_input)
            if match:
                # Purpose of the file.
                purpose = match.group(1)
                # Extract file path.
                file_path = match.group(2)
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    continue
                # Filename.
                file_name = os.path.basename(file_path)
                # Read file content.
                async with aiofiles.open(file_path, "rb") as f:
                    file_content = await f.read()
                if purpose == "code_interpreter":
                    # Upload file.
                    file = await self._client.files.create(file=(file_name, file_content), purpose="assistants")
                    # Get existing file ids from tool resources.
                    thread = await self._client.beta.threads.retrieve(thread_id=self._thread_id)
                    tool_resources: ToolResources = thread.tool_resources if thread.tool_resources else ToolResources()
                    assert tool_resources.code_interpreter is not None
                    if tool_resources.code_interpreter.file_ids:
                        file_ids = tool_resources.code_interpreter.file_ids
                    else:
                        file_ids = [file.id]
                    # Update thread with new file.
                    await self._client.beta.threads.update(
                        thread_id=self._thread_id,
                        tool_resources={"code_interpreter": {"file_ids": file_ids}},
                    )
                elif purpose == "file_search":
                    # Upload file to vector store.
                    file_batch = await self._client.beta.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=self._vector_store_id,
                        files=[(file_name, file_content)],
                    )
                    assert file_batch.status == "completed"
                print(f"Uploaded file: {file_name}")
                continue
            elif user_input.startswith("[upload"):
                print("Invalid upload command. Please use '[upload code_interpreter | file_search filename]'.")
                continue
            elif user_input.strip().lower() == "exit":
                # Exit handler.
                return
            else:
                # Publish user input and exit handler.
                await self.publish_message(
                    TextMessage(content=user_input, source=self.metadata["type"]), topic_id=DefaultTopicId()
                )
                return


class EventHandler(AsyncAssistantEventHandler):
    @override
    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        print(delta.value, end="", flush=True)

    @override
    async def on_run_step_created(self, run_step: RunStep) -> None:
        details = run_step.step_details
        if details.type == "tool_calls":
            for tool in details.tool_calls:
                if tool.type == "code_interpreter":
                    print("\nGenerating code to interpret:\n\n```python")

    @override
    async def on_run_step_done(self, run_step: RunStep) -> None:
        details = run_step.step_details
        if details.type == "tool_calls":
            for tool in details.tool_calls:
                if tool.type == "code_interpreter":
                    print("\n```\nExecuting code...")

    @override
    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        details = delta.step_details
        if details is not None and details.type == "tool_calls":
            for tool in details.tool_calls or []:
                if tool.type == "code_interpreter" and tool.code_interpreter and tool.code_interpreter.input:
                    print(tool.code_interpreter.input, end="", flush=True)

    @override
    async def on_message_created(self, message: Message) -> None:
        print(f"{sep}\nAssistant:\n")

    @override
    async def on_message_done(self, message: Message) -> None:
        # print a citation to the file searched
        if not message.content:
            return
        content = message.content[0]
        if not content.type == "text":
            return
        text_content = content.text
        annotations = text_content.annotations
        citations: List[str] = []
        for index, annotation in enumerate(annotations):
            text_content.value = text_content.value.replace(annotation.text, f"[{index}]")
            if file_citation := getattr(annotation, "file_citation", None):
                client = openai.AsyncClient()
                cited_file = await client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")
        if citations:
            print("\n".join(citations))


async def assistant_chat(runtime: AgentRuntime) -> str:
    oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        description="An AI assistant that helps with everyday tasks.",
        instructions="Help the user with their task.",
        tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
    )
    vector_store = openai.beta.vector_stores.create()
    thread = openai.beta.threads.create(
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )
    await runtime.register(
        "Assistant",
        lambda: OpenAIAssistantAgent(
            description="An AI assistant that helps with everyday tasks.",
            client=openai.AsyncClient(),
            assistant_id=oai_assistant.id,
            thread_id=thread.id,
            assistant_event_handler_factory=lambda: EventHandler(),
        ),
        lambda: [DefaultSubscription()],
    )

    await runtime.register(
        "User",
        lambda: UserProxyAgent(
            client=openai.AsyncClient(),
            assistant_id=oai_assistant.id,
            thread_id=thread.id,
            vector_store_id=vector_store.id,
        ),
        lambda: [DefaultSubscription()],
    )
    # Create a group chat manager to facilitate a turn-based conversation.
    await runtime.register(
        "GroupChatManager",
        lambda: GroupChatManager(
            description="A group chat manager.",
            model_context=BufferedChatCompletionContext(buffer_size=10),
            participants=[
                AgentId("Assistant", AgentInstantiationContext.current_agent_id().key),
                AgentId("User", AgentInstantiationContext.current_agent_id().key),
            ],
        ),
        lambda: [DefaultSubscription()],
    )
    return "User"


async def main() -> None:
    usage = """Chat with an AI assistant backed by OpenAI Assistant API.
You can upload files to the assistant using the command:

[upload code_interpreter | file_search filename]

where 'code_interpreter' or 'file_search' is the purpose of the file and
'filename' is the path to the file. For example:

[upload code_interpreter data.csv]

This will upload data.csv to the assistant for use with the code interpreter tool.

Type "exit" to exit the chat.
"""
    runtime = SingleThreadedAgentRuntime()
    user = await assistant_chat(runtime)
    runtime.start()
    print(usage)
    # Request the user to start the conversation.
    await runtime.send_message(PublishNow(), AgentId(user, "default"))

    # TODO: have a way to exit the loop.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with an AI assistant.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("assistant.log")
        logging.getLogger("autogen_core").addHandler(handler)
    asyncio.run(main())
