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
import dotenv
from pydantic import BaseModel, Field
from azure.ai.projects.aio import (AIProjectClient)
from azure.ai.projects import (_types)
import azure.ai.projects.models as models
from azure.identity.aio import DefaultAzureCredential
import os, time


event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class AzureAIAgentState(BaseModel):
    type: str = Field(default="AzureAIAgentState")
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    initial_message_ids: List[str] = Field(default_factory=list)
    vector_store_id: Optional[str] = None
    uploaded_file_ids: List[str] = Field(default_factory=list)


class AzureAIAgent(BaseChatAgent):
    """
    Azure AI Assistant agent.
    
    
    This agent leverages the Assistant API to create AI assistants with capabilities like:

    * Code interpretation and execution
    * Grounding with bing search
    * File handling and search
    * Custom function calling
    * Multi-turn conversations
    
    Agent name should follow the following format:
        ### Criteria for a valid identifier:
            1. It must start with a letter (A-Z, a-z) or an underscore (_).
            2. It can only contain letters, digits (0-9), or underscores.
            3. It cannot be a keyword (reserved word in Python, like `if`, `def`, `class`, etc.).
            4. It cannot contain spaces or special characters (e.g., @, $, %, etc.).
            5. It cannot start with a digit.

        ### Example usage:
        ```python
        print("hello".isidentifier())  # True
        print("123abc".isidentifier()) # False (starts with a digit)
        print("class".isidentifier())  # True (but it's a keyword)
        print("my_var".isidentifier()) # True
        print("my-var".isidentifier()) # False (contains a hyphen)
        ```
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        project_client: AIProjectClient,
        model: str,
        instructions: str,
        tools: Optional[
            Iterable[
                Union[
                    Literal["file_search", "code_interpreter", "bing_grounding", "azure_ai_search", "azure_function", "sharepoint_grounding"],
                    models.BingGroundingToolDefinition | models.CodeInterpreterToolDefinition 
                    | models.SharepointToolDefinition | models.AzureAISearchToolDefinition | 
                    models.FileSearchToolDefinition | models.AzureFunctionToolDefinition,
                    Tool | Callable[..., Any] | Callable[..., Awaitable[Any]],
                ]
            ]
        ] = None,
        agent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        response_format: Optional["_types.AgentsApiResponseFormatOption"] = None,
        temperature: Optional[float] = None,
        tool_resources: Optional["models.ToolResources"] = None,
        top_p: Optional[float] = None,
    ) -> None:
        super().__init__(name, description)
        
        if tools is None:
            tools = []
        
        self._original_tools: dict[str, Tool] = {}
        
        converted_tools: List["ToolDefinition"] = []
        self._add_tools(tools, converted_tools)
            
        self._project_client = project_client
        self._agent: Optional["Agent"] = None
        self._thread: Optional["AgentThread"] = None
        self._init_thread_id = thread_id
        self._model = model
        self._instructions = instructions
        self._api_tools = converted_tools
        self._agent_id = agent_id
        self._metadata = metadata
        self._response_format = response_format
        self._temperature = temperature
        self._tool_resources = tool_resources
        self._top_p = top_p
        self._vector_store_id: Optional[str] = None
        self._uploaded_file_ids: List[str] = []
        
        self._initial_message_ids: Set[str] = set()
        self._initial_state_retrieved: bool = False


    # Properties
    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the assistant agent produces."""
        return (TextMessage,)

    @property
    def _thread_id(self) -> str:
        if self._thread is None:
            raise ValueError("Thread not initialized")
        return self._thread.id

    @property
    def _get_agent_id(self) -> str:
        if self._agent is None:
            raise ValueError("Agent not initialized")
        return self._agent.id

    # Internal Methods

    def _add_tools(self, tools, converted_tools):
        for tool in tools:
            if isinstance(tool, str):
                if tool == "file_search":
                    converted_tools.append(models.FileSearchToolDefinition())
                elif tool == "code_interpreter":
                    converted_tools.append(models.CodeInterpreterToolDefinition())
                elif tool == "bing_grounding":
                    converted_tools.append(models.BingGroundingToolDefinition())
                elif tool == "azure_ai_search":
                    converted_tools.append(models.AzureAISearchToolDefinition())
                elif tool == "azure_function":
                    converted_tools.append(models.AzureFunctionToolDefinition())
                elif tool == "sharepoint_grounding":
                    converted_tools.append(models.SharepointToolDefinition())
                else:
                    raise ValueError(f"Unsupported tool string: {tool}")
            elif isinstance(tool, models.ToolDefinition):
                converted_tools.append(tool)
            elif isinstance(tool, Tool):
                self._original_tools.append(tool)
                converted_tools.append(self._convert_tool_to_function_tool_definition(tool))
            elif callable(tool):
                if hasattr(tool, "__doc__") and tool.__doc__ is not None:
                    description = tool.__doc__
                else:
                    description = ""
                function_tool = FunctionTool(tool, description=description)
                self._original_tools.append(function_tool)
                converted_tools.append(self._convert_tool_to_function_tool_definition(function_tool))
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")
    
    def _convert_tool_to_function_tool_definition(self, tool: Tool) -> models.FunctionToolDefinition:
        """Convert an autogen Tool to an Azure AI Agent function tool definition."""
        
        schema = tool.schema
        parameters: Dict[str, object] = {}
        
        if "parameters" in schema:
            parameters = {
                "type": schema["parameters"]["type"],
                "properties": schema["parameters"]["properties"],
            }
            if "required" in schema["parameters"]:
                parameters["required"] = schema["parameters"]["required"]
    
        func_definition = models.FunctionDefinition(
            name=tool.name,
            description=tool.description,
            parameters=parameters,
            type=tool.type,
        )
        
        return models.FunctionToolDefinition(
            type="function",
            function=func_definition,
        )

    async def _ensure_initialized(self) -> None:
        """Ensure assistant and thread are created."""
        if self._agent is None:
            if self._agent_id:
                self._agent = await self._project_client.agents.get_agent(agent_id=self._agent_id)
            else:
                self._agent = await self._project_client.agents.create_agent(
                    name=self.name,
                    model=self._model,
                    description=self.description,
                    instructions=self._instructions,
                    tools=self._api_tools,
                    metadata=self._metadata,
                    response_format=self._response_format if self._response_format else None,  # type: ignore
                    temperature=self._temperature,
                    tool_resources=self._tool_resources if self._tool_resources else None,  # type: ignore
                    top_p=self._top_p,
                )

        if self._thread is None:
            if self._init_thread_id:
                self._thread = await self._project_client.agents.get_thread(thread_id=self._init_thread_id)
                
                # Retrieve initial state only once
                if not self._initial_state_retrieved:
                    await self._retrieve_initial_state()
                    self._initial_state_retrieved = True
            else:
                self._thread = await self._project_client.agents.create_thread()
    
    async def _retrieve_initial_state(self) -> None:
        """Retrieve and store the initial state of messages and runs."""
        # Retrieve all initial message IDs
        initial_message_ids: Set[str] = set()
        after: str | None = None
        while True:
            msgs: models.OpenAIPageableListOfThreadMessage = await self._project_client.agents.list_messages(
                thread_id=self._thread_id, after=after, order=models.ListSortOrder.ASCENDING, limit=100)

            for msg in msgs.data:
                initial_message_ids.add(msg.id)
            if not msgs.has_more:
                break
            after = msgs.data[-1].id
        self._initial_message_ids = initial_message_ids
    
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
    
    async def _upload_files(self, file_paths: str | Iterable[str], 
                            purpose: str = "assistant",
                            sleep_interval: float = 0.5,
                            cancellation_token: CancellationToken = CancellationToken()) -> List[str]:
        """Upload files and return their IDs."""
        await self._ensure_initialized()

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        file_ids: List[str] = []
        for file_path in file_paths:
            file_name = os.path.basename(file_path)

            file: models.OpenAIFile = await cancellation_token.link_future(
                asyncio.ensure_future(self._project_client.agents.upload_file_and_poll(file_path=file_path, purpose=purpose, sleep_interval=sleep_interval)))            
            
            if file.status != models.FileState.PROCESSED:
                raise ValueError(f"File upload failed with status {file.status}")
            
            event_logger.debug(f"File uploaded successfully: {file.id}, {file_name}")
            
            file_ids.append(file.id)
            self._uploaded_file_ids.append(file.id)

        return file_ids
    
    # Public Methods
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken = CancellationToken(), message_limit: int = 1) -> Response:
        """Handle incoming messages and return a response."""

        async for message in self.on_messages_stream(messages=messages, cancellation_token=cancellation_token, message_limit=message_limit):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
            self, messages: Sequence[ChatMessage], message_limit: int  = 1, cancellation_token: CancellationToken = CancellationToken()
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
            run: models.ThreadRun = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.create_run(
                        thread_id=self._thread_id,
                        agent_id=self._get_agent_id,
                    )
                )
            )

            # Wait for run completion by polling
            while True:
                run = await cancellation_token.link_future(
                    asyncio.ensure_future(
                        self._project_client.agents.get_run(
                            thread_id=self._thread_id,
                            run_id=run.id,
                        )
                    )
                )

                if run.status == models.RunStatus.FAILED:
                    raise ValueError(f"Run failed: {run.last_error}")

                # If the run requires action (function calls), execute tools and continue
                if run.status == models.RunStatus.REQUIRES_ACTION  and run.required_action is not None:
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
                    
                    # TODO: Support parallel execution of tool calls
                    
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
                            self._project_client.agents.submit_tool_outputs_to_run(
                                thread_id=self._thread_id,
                                run_id=run.id,
                                tool_outputs=[models.ToolOutput(tool_call_id=t.call_id, output=t.content) for t in tool_outputs],
                            )
                        )
                    )
                    continue

                if run.status == models.RunStatus.COMPLETED:
                    break

                #TODO support for parameter to control polling interval
                await asyncio.sleep(0.5) 

            # Get messages after run completion
            agent_messages: models.OpenAIPageableListOfThreadMessage = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.list_messages(thread_id=self._thread_id, order=models.ListSortOrder.DESCENDING, limit=message_limit)
                )
            )

            if not agent_messages.data:
                raise ValueError("No messages received from assistant")

            # Get the last message's content
            last_message = agent_messages.data[0]
            if not last_message.content:
                raise ValueError(f"No content in the last message: {last_message}")

            # Extract text content
            text_content = agent_messages.text_messages
            if not text_content:
                raise ValueError(f"Expected text content in the last message: {last_message.content}")

            # Return the assistant's response as a Response with inner messages
            chat_message = TextMessage(source=self.name, content=text_content[0].text.value)
            yield Response(chat_message=chat_message, inner_messages=inner_messages)
    
    async def handle_text_message(self, content: str, cancellation_token: CancellationToken) -> None:
        """Handle regular text messages by adding them to the thread."""
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.create_message(
                    thread_id=self._thread_id,
                    content=content,
                    role=models.MessageRole.USER,
                )
            )
        )
    
    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Handle reset command by creating a new thread. Currently the Azure AI Agent API has no support for deleting messages."""
        
        self._thread = None
        self._init_thread_id = None
        
        await self._ensure_initialized()
        
        

        
        # Retrieve all message IDs in the thread
        self._thread = await self._project_client.agents.create_thread()
    
    async def save_state(self) -> Mapping[str, Any]:
        state = AzureAIAgentState(
            agent_id= self._agent.id if self._agent else self._agent_id,
            thread_id=self._thread.id if self._thread else self._init_thread_id,
            initial_message_ids=list(self._initial_message_ids),
            vector_store_id=self._vector_store_id,
            uploaded_file_ids=self._uploaded_file_ids,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        agent_state = AzureAIAgentState.model_validate(state)
        self._agent_id = agent_state.agent_id
        self._init_thread_id = agent_state.thread_id
        self._initial_message_ids = set(agent_state.initial_message_ids)
        self._vector_store_id = agent_state.vector_store_id
        self._uploaded_file_ids = agent_state.uploaded_file_ids
    
    async def on_upload_for_code_interpreter(
        self, file_paths: str | Iterable[str], cancellation_token: CancellationToken
    ) -> None:
        """Handle file uploads for the code interpreter."""
        await self._ensure_initialized()

        file_ids = await self._upload_files(file_paths=file_paths, cancellation_token=cancellation_token)

        # Update thread with the new files
        thread: models.AgentThread = await cancellation_token.link_future(
            asyncio.ensure_future(self._project_client.agents.get_thread(thread_id=self._thread_id))
        )
        
        tool_resources: models.ToolResources = thread.tool_resources or models.ToolResources()
        code_interpreter: models.CodeInterpreterTool = (
            tool_resources.code_interpreter or models.CodeInterpreterToolResource()
        )
        existing_file_ids: List[str] = code_interpreter.file_ids or []
        existing_file_ids.extend(file_ids)
        tool_resources.code_interpreter = models.CodeInterpreterToolResource(file_ids=existing_file_ids)

        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.update_thread(
                    thread_id=self._thread_id,
                    tool_resources=tool_resources)
                )
            
            )
  
    async def on_upload_for_file_search(
        self, 
        file_paths: str | Iterable[str], 
        cancellation_token: CancellationToken,
        vector_store_name: Optional[str] = None,
        data_sources: Optional[List[models.VectorStoreDataSource]] = None,
        expires_after: Optional[models.VectorStoreExpirationPolicy] = None,
        chunking_strategy: Optional[models.VectorStoreChunkingStrategyRequest] = None,
        vector_store_metadata: Optional[Dict[str, str]] = None,
        vector_store_polling_sleep_interval: float = 1,
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
            vector_store: models.VectorStore = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.create_vector_store_and_poll(file_ids=[], 
                                                                             name=vector_store_name,
                                                                             data_sources=data_sources,
                                                                             expires_after=expires_after,
                                                                             chunking_strategy=chunking_strategy,
                                                                             metadata=vector_store_metadata,
                                                                             sleep_interval=vector_store_polling_sleep_interval))
            )
            self._vector_store_id = vector_store.id

            # Update assistant with vector store ID
            await cancellation_token.link_future(
                asyncio.ensure_future(self._project_client.agents.update_agent(
                        agent_id=self._get_agent_id,
                        tools=self._api_tools,
                        tool_resources=models.ToolResources(
                            file_search=models.FileSearchToolResource(vector_store_ids=[self._vector_store_id])
                        ),
                    )
                )
            )

        file_ids = await self._upload_files(file_paths=file_paths, cancellation_token=cancellation_token, purpose=models.FilePurpose.AGENTS)
        
        # Create file batch with the file IDs
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.create_vector_store_file_batch_and_poll(vector_store_id=self._vector_store_id, file_ids=file_ids)
            )
        )
    
async def main():
    async with DefaultAzureCredential() as credential:
        
        async with  AIProjectClient.from_connection_string(credential=credential,
                                                           conn_str=os.getenv("AI_PROJECT_CONNECTION_STRING"),
        ) as project_client:
                
                conn = await project_client.connections.get(connection_name="gwbsglobal01")
                
                #Example of using the AzureAIAgent with a bing grounding tool
                
                bing_tool = models.BingGroundingTool(conn.id)
                
                agent_with_bing_grounding = AzureAIAgent(
                        name="my_agent",
                        description="This is a test agent",
                        project_client=project_client,
                        model="gpt-4o",
                        instructions="You are a helpful assistant.",
                        tools=bing_tool.definitions,
                        metadata={"source": "Autogen_AzureAIAgent"},
                        
                )
                
                file_search_tool = models.FileSearchToolDefinition()
                
                agent_with_file_search_tool = AzureAIAgent(
                        name="my_agent_file_search",
                        description="This is a test agent",
                        project_client=project_client,
                        model="gpt-4o",
                        instructions="You are a helpful assistant.",
                        tools=["file_search"],
                        metadata={"source": "Autogen_AzureAIAgent"},
                )
                
                # Example of using the AzureAIAgent with bing grounding
                current_active_agent = agent_with_bing_grounding
                result = await current_active_agent.on_messages(messages=[TextMessage(content="What is microsoft annual leave policy?", source="user")], 
                                                                cancellation_token=CancellationToken(), 
                                                                message_limit=5)
                
                
                # Example of using the AzureAIAgent with file search grounding
                # current_active_agent = agent_with_file_search_tool
                # await current_active_agent.on_upload_for_file_search(
                #     file_paths=["/workspaces/autogen/python/packages/autogen-core/docs/src/user-guide/core-user-guide/faqs.md"],
                #     vector_store_name="file_upload_index",
                #     vector_store_metadata={"source": "Autogen_AzureAIAgent"},
                #     cancellation_token=CancellationToken(),
                # )
                
                # result = await current_active_agent.on_messages(messages=[TextMessage(content="Summarize the main points of the faqs", source="user")], 
                #                                                 cancellation_token=CancellationToken(),
                #                                                 message_limit=5)
                
                
                print(result)

if __name__ == "__main__":
    # Example usage of AzureAIAgent
    # Replace with your actual connection string and credentials
    dotenv.load_dotenv()
    asyncio.run(main())
    
    
    """
        TOOD:
        [] Support for file upload
        [] Support for sharepoint grounding
        [] Support for azure function grounding
        [] Support for file search
        [] Support for custom function calling
        [] Add metadata to the thread (agent_id, source ="AUTODGEN_AGENT")
    """

