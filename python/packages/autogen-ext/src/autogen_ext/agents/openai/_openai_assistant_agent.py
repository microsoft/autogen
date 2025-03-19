import asyncio
import json
import logging
import os
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Union,
    cast,
)

import aiofiles
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models._model_client import ChatCompletionClient
from autogen_core.models._types import FunctionExecutionResult
from autogen_core.tools import FunctionTool, Tool
from pydantic import BaseModel, Field

from openai import NOT_GIVEN, AsyncAzureOpenAI, AsyncOpenAI, NotGiven
from openai.pagination import AsyncCursorPage
from openai.resources.beta.threads import AsyncMessages, AsyncRuns, AsyncThreads
from openai.types import FileObject
from openai.types.beta import thread_update_params
from openai.types.beta.assistant import Assistant
from openai.types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam
from openai.types.beta.assistant_tool_param import AssistantToolParam
from openai.types.beta.code_interpreter_tool_param import CodeInterpreterToolParam
from openai.types.beta.file_search_tool_param import FileSearchToolParam
from openai.types.beta.function_tool_param import FunctionToolParam
from openai.types.beta.thread import Thread, ToolResources, ToolResourcesCodeInterpreter
from openai.types.beta.threads import Message, MessageDeleted, Run
from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.vector_store import VectorStore

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


def _convert_tool_to_function_param(tool: Tool) -> "FunctionToolParam":
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


class OpenAIAssistantAgentState(BaseModel):
    type: str = Field(default="OpenAIAssistantAgentState")
    assistant_id: Optional[str] = None
    thread_id: Optional[str] = None
    initial_message_ids: List[str] = Field(default_factory=list)
    vector_store_id: Optional[str] = None
    uploaded_file_ids: List[str] = Field(default_factory=list)


class OpenAIAssistantAgent(BaseChatAgent):
    """An agent implementation that uses the Assistant API to generate responses.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[openai]"
        # pip install "autogen-ext[openai,azure]"  # For Azure OpenAI Assistant


    This agent leverages the Assistant API to create AI assistants with capabilities like:

    * Code interpretation and execution
    * File handling and search
    * Custom function calling
    * Multi-turn conversations

    The agent maintains a thread of conversation and can use various tools including

    * Code interpreter: For executing code and working with files
    * File search: For searching through uploaded documents
    * Custom functions: For extending capabilities with user-defined tools

    Key Features:

    * Supports multiple file formats including code, documents, images
    * Can handle up to 128 tools per assistant
    * Maintains conversation context in threads
    * Supports file uploads for code interpreter and search
    * Vector store integration for efficient file search
    * Automatic file parsing and embedding

    You can use an existing thread or assistant by providing the `thread_id` or `assistant_id` parameters.

    Examples:

        Use the assistant to analyze data in a CSV file:

        .. code-block:: python

            from openai import AsyncOpenAI
            from autogen_core import CancellationToken
            import asyncio
            from autogen_ext.agents.openai import OpenAIAssistantAgent
            from autogen_agentchat.messages import TextMessage


            async def example():
                cancellation_token = CancellationToken()

                # Create an OpenAI client
                client = AsyncOpenAI(api_key="your-api-key", base_url="your-base-url")

                # Create an assistant with code interpreter
                assistant = OpenAIAssistantAgent(
                    name="Python Helper",
                    description="Helps with Python programming",
                    client=client,
                    model="gpt-4",
                    instructions="You are a helpful Python programming assistant.",
                    tools=["code_interpreter"],
                )

                # Upload files for the assistant to use
                await assistant.on_upload_for_code_interpreter("data.csv", cancellation_token)

                # Get response from the assistant
                response = await assistant.on_messages(
                    [TextMessage(source="user", content="Analyze the data in data.csv")], cancellation_token
                )

                print(response)

                # Clean up resources
                await assistant.delete_uploaded_files(cancellation_token)
                await assistant.delete_assistant(cancellation_token)


            asyncio.run(example())

        Use Azure OpenAI Assistant with AAD authentication:

        .. code-block:: python

            from openai import AsyncAzureOpenAI
            import asyncio
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            from autogen_core import CancellationToken
            from autogen_ext.agents.openai import OpenAIAssistantAgent
            from autogen_agentchat.messages import TextMessage


            async def example():
                cancellation_token = CancellationToken()

                # Create an Azure OpenAI client
                token_provider = get_bearer_token_provider(DefaultAzureCredential())
                client = AsyncAzureOpenAI(
                    azure_deployment="YOUR_AZURE_DEPLOYMENT",
                    api_version="YOUR_API_VERSION",
                    azure_endpoint="YOUR_AZURE_ENDPOINT",
                    azure_ad_token_provider=token_provider,
                )

                # Create an assistant with code interpreter
                assistant = OpenAIAssistantAgent(
                    name="Python Helper",
                    description="Helps with Python programming",
                    client=client,
                    model="gpt-4o",
                    instructions="You are a helpful Python programming assistant.",
                    tools=["code_interpreter"],
                )

                # Get response from the assistant
                response = await assistant.on_messages([TextMessage(source="user", content="Hello.")], cancellation_token)

                print(response)

                # Clean up resources
                await assistant.delete_assistant(cancellation_token)


            asyncio.run(example())

    Args:
        name (str): Name of the assistant
        description (str): Description of the assistant's purpose
        client (AsyncOpenAI | AsyncAzureOpenAI): OpenAI client or Azure OpenAI client instance
        model (str): Model to use (e.g. "gpt-4")
        instructions (str): System instructions for the assistant
        tools (Optional[Iterable[Union[Literal["code_interpreter", "file_search"], Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]]]]): Tools the assistant can use
        assistant_id (Optional[str]): ID of existing assistant to use
        thread_id (Optional[str]): ID of existing thread to use
        metadata (Optional[Dict[str, str]]): Additional metadata for the assistant.
        response_format (Optional[AssistantResponseFormatOptionParam]): Response format settings
        temperature (Optional[float]): Temperature for response generation
        tool_resources (Optional[ToolResources]): Additional tool configuration
        top_p (Optional[float]): Top p sampling parameter
    """

    def __init__(
        self,
        name: str,
        description: str,
        client: AsyncOpenAI | AsyncAzureOpenAI,
        model: str,
        instructions: str,
        tools: Optional[
            Iterable[
                Union[
                    Literal["code_interpreter", "file_search"],
                    Tool | Callable[..., Any] | Callable[..., Awaitable[Any]],
                ]
            ]
        ] = None,
        assistant_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        response_format: Optional["AssistantResponseFormatOptionParam"] = None,
        temperature: Optional[float] = None,
        tool_resources: Optional["ToolResources"] = None,
        top_p: Optional[float] = None,
    ) -> None:
        if isinstance(client, ChatCompletionClient):
            raise ValueError(
                "Incorrect client passed to OpenAIAssistantAgent. Please use an OpenAI AsyncClient instance instead of an AutoGen ChatCompletionClient instance."
            )

        super().__init__(name, description)
        if tools is None:
            tools = []

        # Store original tools and converted tools separately
        self._original_tools: List[Tool] = []
        converted_tools: List["AssistantToolParam"] = []
        for tool in tools:
            if isinstance(tool, str):
                if tool == "code_interpreter":
                    converted_tools.append(CodeInterpreterToolParam(type="code_interpreter"))
                elif tool == "file_search":
                    converted_tools.append(FileSearchToolParam(type="file_search"))
            elif isinstance(tool, Tool):
                self._original_tools.append(tool)
                converted_tools.append(_convert_tool_to_function_param(tool))
            elif callable(tool):
                if hasattr(tool, "__doc__") and tool.__doc__ is not None:
                    description = tool.__doc__
                else:
                    description = ""
                function_tool = FunctionTool(tool, description=description)
                self._original_tools.append(function_tool)
                converted_tools.append(_convert_tool_to_function_param(function_tool))
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")

        self._client = client
        self._assistant: Optional["Assistant"] = None
        self._thread: Optional["Thread"] = None
        self._init_thread_id = thread_id
        self._model = model
        self._instructions = instructions
        self._api_tools = converted_tools
        self._assistant_id = assistant_id
        self._metadata = metadata
        self._response_format = response_format
        self._temperature = temperature
        self._tool_resources = tool_resources
        self._top_p = top_p
        self._vector_store_id: Optional[str] = None
        self._uploaded_file_ids: List[str] = []

        # Variables to track initial state
        self._initial_message_ids: Set[str] = set()
        self._initial_state_retrieved: bool = False

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
                    tools=self._api_tools,
                    metadata=self._metadata,
                    response_format=self._response_format if self._response_format else NOT_GIVEN,  # type: ignore
                    temperature=self._temperature,
                    tool_resources=self._tool_resources if self._tool_resources else NOT_GIVEN,  # type: ignore
                    top_p=self._top_p,
                )

        if self._thread is None:
            if self._init_thread_id:
                self._thread = await self._client.beta.threads.retrieve(thread_id=self._init_thread_id)
            else:
                self._thread = await self._client.beta.threads.create()

        # Retrieve initial state only once
        if not self._initial_state_retrieved:
            await self._retrieve_initial_state()
            self._initial_state_retrieved = True

    async def _retrieve_initial_state(self) -> None:
        """Retrieve and store the initial state of messages and runs."""
        # Retrieve all initial message IDs
        initial_message_ids: Set[str] = set()
        after: str | NotGiven = NOT_GIVEN
        while True:
            msgs: AsyncCursorPage[Message] = await self._client.beta.threads.messages.list(
                self._thread_id, after=after, order="asc", limit=100
            )
            for msg in msgs.data:
                initial_message_ids.add(msg.id)
            if not msgs.has_next_page():
                break
            after = msgs.data[-1].id
        self._initial_message_ids = initial_message_ids

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the assistant agent produces."""
        return (TextMessage,)

    @property
    def threads(self) -> AsyncThreads:
        return self._client.beta.threads

    @property
    def runs(self) -> AsyncRuns:
        return self._client.beta.threads.runs

    @property
    def messages(self) -> AsyncMessages:
        return self._client.beta.threads.messages

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

    async def _execute_tool_call(self, tool_call: FunctionCall, cancellation_token: CancellationToken) -> str:
        """Execute a tool call and return the result."""
        if not self._original_tools:
            raise ValueError("No tools are available.")
        tool = next((t for t in self._original_tools if t.name == tool_call.name), None)
        if tool is None:
            raise ValueError(f"The tool '{tool_call.name}' is not available.")
        arguments = json.loads(tool_call.arguments)
        result = await tool.run_json(arguments, cancellation_token)
        return tool.return_value_as_string(result)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handle incoming messages and return a response."""

        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """Handle incoming messages and return a response."""
        await self._ensure_initialized()

        # Process all messages in sequence
        for message in messages:
            if isinstance(message, (TextMessage, MultiModalMessage)):
                await self.handle_text_message(str(message.content), cancellation_token)
            elif isinstance(message, (StopMessage, HandoffMessage)):
                await self.handle_text_message(message.content, cancellation_token)

        # Inner messages for tool calls
        inner_messages: List[AgentEvent | ChatMessage] = []

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
        while True:
            run = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.runs.retrieve(
                        thread_id=self._thread_id,
                        run_id=run.id,
                    )
                )
            )

            if run.status == "failed":
                raise ValueError(f"Run failed: {run.last_error}")

            # If the run requires action (function calls), execute tools and continue
            if run.status == "requires_action" and run.required_action is not None:
                tool_calls: List[FunctionCall] = []
                for required_tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    if required_tool_call.type == "function":
                        tool_calls.append(
                            FunctionCall(
                                id=required_tool_call.id,
                                name=required_tool_call.function.name,
                                arguments=required_tool_call.function.arguments,
                            )
                        )

                # Add tool call message to inner messages
                tool_call_msg = ToolCallRequestEvent(source=self.name, content=tool_calls)
                inner_messages.append(tool_call_msg)
                event_logger.debug(tool_call_msg)
                yield tool_call_msg

                # Execute tool calls and get results
                tool_outputs: List[FunctionExecutionResult] = []
                for tool_call in tool_calls:
                    try:
                        result = await self._execute_tool_call(tool_call, cancellation_token)
                        is_error = False
                    except Exception as e:
                        result = f"Error: {e}"
                        is_error = True
                    tool_outputs.append(
                        FunctionExecutionResult(
                            content=result, call_id=tool_call.id, is_error=is_error, name=tool_call.name
                        )
                    )

                # Add tool result message to inner messages
                tool_result_msg = ToolCallExecutionEvent(source=self.name, content=tool_outputs)
                inner_messages.append(tool_result_msg)
                event_logger.debug(tool_result_msg)
                yield tool_result_msg

                # Submit tool outputs back to the run
                run = await cancellation_token.link_future(
                    asyncio.ensure_future(
                        self._client.beta.threads.runs.submit_tool_outputs(
                            thread_id=self._thread_id,
                            run_id=run.id,
                            tool_outputs=[{"tool_call_id": t.call_id, "output": t.content} for t in tool_outputs],
                        )
                    )
                )
                continue

            if run.status == "completed":
                break

            await asyncio.sleep(0.5)

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

        # Return the assistant's response as a Response with inner messages
        chat_message = TextMessage(source=self.name, content=text_content[0].text.value)
        yield Response(chat_message=chat_message, inner_messages=inner_messages)

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
        """Handle reset command by deleting new messages and runs since initialization."""
        await self._ensure_initialized()

        # Retrieve all message IDs in the thread
        new_message_ids: List[str] = []
        after: str | NotGiven = NOT_GIVEN
        while True:
            msgs: AsyncCursorPage[Message] = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.messages.list(self._thread_id, after=after, order="asc", limit=100)
                )
            )
            for msg in msgs.data:
                if msg.id not in self._initial_message_ids:
                    new_message_ids.append(msg.id)
            if not msgs.has_next_page():
                break
            after = msgs.data[-1].id

        # Delete new messages
        for msg_id in new_message_ids:
            status: MessageDeleted = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._client.beta.threads.messages.delete(message_id=msg_id, thread_id=self._thread_id)
                )
            )
            assert status.deleted is True

    async def _upload_files(self, file_paths: str | Iterable[str], cancellation_token: CancellationToken) -> List[str]:
        """Upload files and return their IDs."""
        await self._ensure_initialized()

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        file_ids: List[str] = []
        for file_path in file_paths:
            async with aiofiles.open(file_path, mode="rb") as f:
                file_content = await cancellation_token.link_future(asyncio.ensure_future(f.read()))
            file_name = os.path.basename(file_path)

            file: FileObject = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.files.create(file=(file_name, file_content), purpose="assistants"))
            )
            file_ids.append(file.id)
            self._uploaded_file_ids.append(file.id)

        return file_ids

    async def on_upload_for_code_interpreter(
        self, file_paths: str | Iterable[str], cancellation_token: CancellationToken
    ) -> None:
        """Handle file uploads for the code interpreter."""
        await self._ensure_initialized()

        file_ids = await self._upload_files(file_paths, cancellation_token)

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
        await self._ensure_initialized()

        # Check if file_search is enabled in tools
        if not any(tool.get("type") == "file_search" for tool in self._api_tools):
            raise ValueError(
                "File search is not enabled for this assistant. Add a file_search tool when creating the assistant."
            )

        # Create vector store if not already created
        if self._vector_store_id is None:
            vector_store: VectorStore = await cancellation_token.link_future(
                asyncio.ensure_future(self._client.vector_stores.create())
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

        file_ids = await self._upload_files(file_paths, cancellation_token)

        # Create file batch with the file IDs
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=self._vector_store_id, file_ids=file_ids
                )
            )
        )

    async def delete_uploaded_files(self, cancellation_token: CancellationToken) -> None:
        """Delete all files that were uploaded by this agent instance."""
        await self._ensure_initialized()
        for file_id in self._uploaded_file_ids:
            try:
                await cancellation_token.link_future(asyncio.ensure_future(self._client.files.delete(file_id=file_id)))
            except Exception as e:
                event_logger.error(f"Failed to delete file {file_id}: {str(e)}")
        self._uploaded_file_ids = []

    async def delete_assistant(self, cancellation_token: CancellationToken) -> None:
        """Delete the assistant if it was created by this instance."""
        await self._ensure_initialized()
        if self._assistant is not None and not self._assistant_id:
            try:
                await cancellation_token.link_future(
                    asyncio.ensure_future(self._client.beta.assistants.delete(assistant_id=self._get_assistant_id))
                )
                self._assistant = None
            except Exception as e:
                event_logger.error(f"Failed to delete assistant: {str(e)}")

    async def delete_vector_store(self, cancellation_token: CancellationToken) -> None:
        """Delete the vector store if it was created by this instance."""
        await self._ensure_initialized()
        if self._vector_store_id is not None:
            try:
                await cancellation_token.link_future(
                    asyncio.ensure_future(self._client.vector_stores.delete(vector_store_id=self._vector_store_id))
                )
                self._vector_store_id = None
            except Exception as e:
                event_logger.error(f"Failed to delete vector store: {str(e)}")

    async def save_state(self) -> Mapping[str, Any]:
        state = OpenAIAssistantAgentState(
            assistant_id=self._assistant.id if self._assistant else self._assistant_id,
            thread_id=self._thread.id if self._thread else self._init_thread_id,
            initial_message_ids=list(self._initial_message_ids),
            vector_store_id=self._vector_store_id,
            uploaded_file_ids=self._uploaded_file_ids,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        agent_state = OpenAIAssistantAgentState.model_validate(state)
        self._assistant_id = agent_state.assistant_id
        self._init_thread_id = agent_state.thread_id
        self._initial_message_ids = set(agent_state.initial_message_ids)
        self._vector_store_id = agent_state.vector_store_id
        self._uploaded_file_ids = agent_state.uploaded_file_ids
