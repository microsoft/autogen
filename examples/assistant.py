"""This is an example of a chat with an OpenAIAssistantAgent.
You must have OPENAI_API_KEY set up in your environment to
run this example.
"""

import os
import re
from typing import Any, List

import aiofiles
import openai
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.patterns.group_chat import GroupChatOutput
from agnext.chat.patterns.two_agent_chat import TwoAgentChat
from agnext.chat.types import RespondNow, TextMessage
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken
from openai import AsyncAssistantEventHandler
from openai.types.beta.thread import ToolResources
from openai.types.beta.threads import Message, Text, TextDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from typing_extensions import override


class TwoAgentChatOutput(GroupChatOutput):  # type: ignore
    def on_message_received(self, message: Any) -> None:
        pass

    def get_output(self) -> Any:
        return None

    def reset(self) -> None:
        pass


sep = "-" * 50


class UserProxyAgent(BaseChatAgent, TypeRoutedAgent):  # type: ignore
    def __init__(
        self,
        name: str,
        runtime: AgentRuntime,
        client: openai.AsyncClient,
        assistant_id: str,
        thread_id: str,
        vector_store_id: str,
    ) -> None:  # type: ignore
        super().__init__(
            name=name,
            description="A human user",
            runtime=runtime,
        )
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._vector_store_id = vector_store_id

    @message_handler()  # type: ignore
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        # TODO: render image if message has image.
        # print(f"{message.source}: {message.content}")
        pass

    @message_handler()  # type: ignore
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> TextMessage:  # type: ignore
        while True:
            user_input = input(f"\n{sep}\nYou: ")
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
            else:
                # Send user input to assistant.
                return TextMessage(content=user_input, source=self.name)


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


def assistant_chat(runtime: AgentRuntime) -> TwoAgentChat:  # type: ignore
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
    assistant = OpenAIAssistantAgent(
        name="Assistant",
        description="An AI assistant that helps with everyday tasks.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=oai_assistant.id,
        thread_id=thread.id,
        assistant_event_handler_factory=lambda: EventHandler(),
    )
    user = UserProxyAgent(
        name="User",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=oai_assistant.id,
        thread_id=thread.id,
        vector_store_id=vector_store.id,
    )
    return TwoAgentChat(
        name="AssistantChat",
        description="A chat with an AI assistant",
        runtime=runtime,
        first_speaker=assistant,
        second_speaker=user,
        num_rounds=100,
        output=TwoAgentChatOutput(),
    )


async def main() -> None:
    usage = """Chat with an AI assistant backed by OpenAI Assistant API.
You can upload files to the assistant using the command:

[upload code_interpreter | file_search filename]

where 'code_interpreter' or 'file_search' is the purpose of the file and
'filename' is the path to the file. For example:

[upload code_interpreter data.csv]

This will upload data.csv to the assistant for use with the code interpreter tool.
"""
    runtime = SingleThreadedAgentRuntime()
    chat = assistant_chat(runtime)
    print(usage)
    future = runtime.send_message(
        TextMessage(content="Hello.", source="User"),
        chat,
    )
    while not future.done():
        await runtime.process_next()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
