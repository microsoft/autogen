import asyncio
import json
import logging
import os
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
)

from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    AgentEvent,
    BaseChatMessage,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models._types import FunctionExecutionResult
from autogen_core.tools import FunctionTool, Tool

import azure.ai.projects.models as models
from azure.ai.projects import _types
from azure.ai.projects.aio import AIProjectClient

from ._types import AzureAIAgentState, ListToolType

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class AzureAIAgent(BaseChatAgent):
    """
    Azure AI Assistant agent for AutoGen.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[azure]"  # For Azure AI Foundry Agent Service

    This agent leverages the Azure AI Assistant API to create AI assistants with capabilities like:

    * Code interpretation and execution
    * Grounding with Bing search
    * File handling and search
    * Custom function calling
    * Multi-turn conversations

    The agent integrates with AutoGen's messaging system, providing a seamless way to use Azure AI
    capabilities within the AutoGen framework. It supports tools like code interpreter,
    file search, and various grounding mechanisms.

    Agent name must be a valid Python identifier:
        1. It must start with a letter (A-Z, a-z) or an underscore (_).
        2. It can only contain letters, digits (0-9), or underscores.
        3. It cannot be a Python keyword.
        4. It cannot contain spaces or special characters.
        5. It cannot start with a digit.


    Check here on how to create a new secured agent with user-managed identity:
    https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/virtual-networks

    Examples:

        Use the AzureAIAgent to create an agent grounded with Bing:

        .. code-block:: python

            import asyncio
            import os

            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
            from autogen_ext.agents.azure._azure_ai_agent import AzureAIAgent
            from azure.ai.projects.aio import AIProjectClient
            from azure.identity.aio import DefaultAzureCredential


            async def bing_example():
                credential = DefaultAzureCredential()

                async with AIProjectClient.from_connection_string(
                    credential=credential, conn_str=os.getenv("AI_PROJECT_CONNECTION_STRING", "")
                ) as project_client:
                    conn = await project_client.connections.get(connection_name=os.getenv("BING_CONNECTION_NAME", None))

                    bing_tool = models.BingGroundingTool(conn.id)
                    agent_with_bing_grounding = AzureAIAgent(
                        name="bing_agent",
                        description="An AI assistant with Bing grounding",
                        project_client=project_client,
                        deployment_name="gpt-4o",
                        instructions="You are a helpful assistant.",
                        tools=bing_tool.definitions,
                        metadata={"source": "AzureAIAgent"},
                    )

                    result = await agent_with_bing_grounding.on_messages(
                        messages=[TextMessage(content="What is Microsoft's annual leave policy?", source="user")],
                        cancellation_token=CancellationToken(),
                        message_limit=5,
                    )
                    print(result)


            if __name__ == "__main__":
                dotenv.load_dotenv()
                asyncio.run(bing_example())

        Use the AzureAIAgent to create an agent with file search capability:

        .. code-block:: python

            import asyncio
            import os

            import dotenv
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
            from autogen_ext.agents.azure._azure_ai_agent import AzureAIAgent
            from azure.ai.projects.aio import AIProjectClient
            from azure.identity.aio import DefaultAzureCredential


            async def file_search_example():
                credential = DefaultAzureCredential()
                async with AIProjectClient.from_connection_string(
                    credential=credential, conn_str=os.getenv("AI_PROJECT_CONNECTION_STRING", "")
                ) as project_client:
                    agent_with_file_search = AzureAIAgent(
                        name="file_search_agent",
                        description="An AI assistant with file search capabilities",
                        project_client=project_client,
                        deployment_name="gpt-4o",
                        instructions="You are a helpful assistant.",
                        tools=["file_search"],
                        metadata={"source": "AzureAIAgent"},
                    )

                    await agent_with_file_search.on_upload_for_file_search(
                        file_paths=[
                            "/workspaces/autogen/python/packages/autogen-core/docs/src/user-guide/core-user-guide/cookbook/data/product_info_1.md"
                        ],
                        vector_store_name="file_upload_index",
                        vector_store_metadata={"source": "AzureAIAgent"},
                        cancellation_token=CancellationToken(),
                    )
                    result = await agent_with_file_search.on_messages(
                        messages=[TextMessage(content="Hello, what Contoso products do you know?", source="user")],
                        cancellation_token=CancellationToken(),
                        message_limit=5,
                    )
                    print(result)

                if __name__ == "__main__":
                    dotenv.load_dotenv()
                    asyncio.run(file_search_example())

        Use the AzureAIAgent to create an agent with code interpreter capability:

        .. code-block:: python

            import asyncio
            import os

            import dotenv
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
            from autogen_ext.agents.azure._azure_ai_agent import AzureAIAgent
            from azure.ai.projects.aio import AIProjectClient
            from azure.identity.aio import DefaultAzureCredential


            async def code_interpreter_example():
                credential = DefaultAzureCredential()
                async with AIProjectClient.from_connection_string(
                    credential=credential, conn_str=os.getenv("AI_PROJECT_CONNECTION_STRING", "")
                ) as project_client:
                    agent_with_code_interpreter = AzureAIAgent(
                        name="code_interpreter_agent",
                        description="An AI assistant with code interpreter capabilities",
                        project_client=project_client,
                        deployment_name="gpt-4o",
                        instructions="You are a helpful assistant.",
                        tools=["code_interpreter"],
                        metadata={"source": "AzureAIAgent"},
                    )

                    await agent_with_code_interpreter.on_upload_for_code_interpreter(
                        file_paths="/workspaces/autogen/python/packages/autogen-core/docs/src/user-guide/core-user-guide/cookbook/data/nifty_500_quarterly_results.csv",
                        cancellation_token=CancellationToken(),
                    )

                    result = await agent_with_code_interpreter.on_messages(
                        messages=[
                            TextMessage(
                                content="Aggregate the number of stocks per industry and give me a markdown table as a result?",
                                source="user",
                            )
                        ],
                        cancellation_token=CancellationToken(),
                    )

                    print(result)


            if __name__ == "__main__":
                dotenv.load_dotenv()
                asyncio.run(code_interpreter_example())
    """

    def __init__(
        self,
        name: str,
        description: str,
        project_client: AIProjectClient,
        deployment_name: str,
        instructions: str,
        tools: Optional[ListToolType] = None,
        agent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        response_format: Optional["_types.AgentsApiResponseFormatOption"] = None,
        temperature: Optional[float] = None,
        tool_resources: Optional["models.ToolResources"] = None,
        top_p: Optional[float] = None,
    ) -> None:
        """
        Initialize the Azure AI Agent.

        Args:
            name (str): The name of the agent. Must be a valid Python identifier.
            description (str): A brief description of the agent's purpose.
            project_client (AIProjectClient): The Azure AI Project client for API interactions.
            deployment_name (str): The model deployment name to use for the agent (e.g., "gpt-4").
            instructions (str): Detailed instructions for the agent's behavior.
            tools (Optional[Iterable[Union[str, ToolDefinition, Tool, Callable]]]): A list of tools the agent can use.
                Supported string values: "file_search", "code_interpreter", "bing_grounding",
                "azure_ai_search", "azure_function", "sharepoint_grounding".
            agent_id (Optional[str]): Existing agent ID to use instead of creating a new one.
            thread_id (Optional[str]): Existing thread ID to continue a conversation.
            metadata (Optional[Dict[str, str]]): Additional metadata for the agent.
            response_format (Optional[_types.AgentsApiResponseFormatOption]): Format options for the agent's responses.
            temperature (Optional[float]): Sampling temperature, controls randomness of output.
            tool_resources (Optional[models.ToolResources]): Resources configuration for agent tools.
            top_p (Optional[float]): An alternative to temperature, nucleus sampling parameter.

        Raises:
            ValueError: If an unsupported tool type is provided.
        """
        super().__init__(name, description)

        if tools is None:
            tools = []

        self._original_tools: list[Tool] = []

        converted_tools: List["models.ToolDefinition"] = []
        self._add_tools(tools, converted_tools)

        self._project_client = project_client
        self._agent: Optional["models.Agent"] = None
        self._thread: Optional["models.AgentThread"] = None
        self._init_thread_id = thread_id
        self._deployment_name = deployment_name
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
    def thread_id(self) -> str:
        if self._thread is None:
            raise ValueError("Thread not initialized")
        return self._thread.id

    @property
    def _get_agent_id(self) -> str:
        if self._agent is None:
            raise ValueError("Agent not initialized")
        return self._agent.id

    @property
    def description(self) -> str:
        if not self._description:
            raise ValueError("Description not initialized")
        return self._description

    @property
    def agent_id(self) -> str:
        if not self._agent_id:
            raise ValueError("Agent not initialized")
        return self._agent_id

    @property
    def deployment_name(self) -> str:
        if not self._deployment_name:
            raise ValueError("Deployment name not initialized")
        return self._deployment_name

    @property
    def instructions(self) -> str:
        if not self._instructions:
            raise ValueError("Instructions not initialized")
        return self._instructions

    @property
    def tools(self) -> List[models.ToolDefinition]:
        """
        Get the list of tools available to the agent.

        Returns:
            List[models.ToolDefinition]: The list of tool definitions.
        """
        return self._api_tools

    def _add_tools(self, tools: Optional[ListToolType], converted_tools: List["models.ToolDefinition"]) -> None:
        """
        Convert various tool formats to Azure AI Agent tool definitions.

        Args:
            tools: List of tools in various formats (string identifiers, ToolDefinition objects, Tool objects, or callables)
            converted_tools: List to which converted tool definitions will be added

        Raises:
            ValueError: If an unsupported tool type is provided
        """
        if tools is None:
            return

        for tool in tools:
            if isinstance(tool, str):
                if tool == "file_search":
                    converted_tools.append(models.FileSearchToolDefinition())
                elif tool == "code_interpreter":
                    converted_tools.append(models.CodeInterpreterToolDefinition())
                elif tool == "bing_grounding":
                    converted_tools.append(models.BingGroundingToolDefinition())  # type: ignore
                elif tool == "azure_ai_search":
                    converted_tools.append(models.AzureAISearchToolDefinition())
                elif tool == "azure_function":
                    converted_tools.append(models.AzureFunctionToolDefinition())  # type: ignore
                elif tool == "sharepoint_grounding":
                    converted_tools.append(models.SharepointToolDefinition())  # type: ignore
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
        """
        Convert an autogen Tool to an Azure AI Agent function tool definition.

        Args:
            tool (Tool): The AutoGen tool to convert

        Returns:
            models.FunctionToolDefinition: A function tool definition compatible with Azure AI Agent API
        """

        schema = tool.schema
        parameters: Dict[str, object] = {}

        if "parameters" in schema:
            parameters = {
                "type": schema["parameters"]["type"],
                "properties": schema["parameters"]["properties"],
            }
            if "required" in schema["parameters"]:
                parameters["required"] = schema["parameters"]["required"]

        func_definition = models.FunctionDefinition(name=tool.name, description=tool.description, parameters=parameters)

        return models.FunctionToolDefinition(
            function=func_definition,
        )

    async def _ensure_initialized(self, create_new_thread: bool = False, create_new_agent: bool = False) -> None:
        """
        Ensure agent and thread are properly initialized before operations.

        This method ensures that both the Azure AI Agent and thread are created or retrieved
        from existing IDs. It also handles retrieving the initial state of an existing thread
        when needed.

        Args:
            create_new_thread (bool): When True, creates a new thread even if thread_id is provided
            create_new_agent (bool): When True, creates a new agent even if agent_id is provided

        Raises:
            ValueError: If agent or thread creation fails
        """
        if self._agent is None or create_new_agent:
            if self._agent_id and create_new_agent is False:
                self._agent = await self._project_client.agents.get_agent(agent_id=self._agent_id)
            else:
                self._agent = await self._project_client.agents.create_agent(
                    name=self.name,
                    model=self._deployment_name,
                    description=self.description,
                    instructions=self._instructions,
                    tools=self._api_tools,
                    metadata=self._metadata,
                    response_format=self._response_format if self._response_format else None,  # type: ignore
                    temperature=self._temperature,
                    tool_resources=self._tool_resources if self._tool_resources else None,  # type: ignore
                    top_p=self._top_p,
                )

        if self._thread is None or create_new_thread:
            if self._init_thread_id and create_new_thread is False:
                self._thread = await self._project_client.agents.get_thread(thread_id=self._init_thread_id)
                # Retrieve initial state only once
                if not self._initial_state_retrieved:
                    await self._retrieve_initial_state()
                    self._initial_state_retrieved = True
            else:
                self._thread = await self._project_client.agents.create_thread()

    async def _retrieve_initial_state(self) -> None:
        """
        Retrieve and store the initial state of messages in the thread.

        This method retrieves all message IDs from an existing thread to track which
        messages were present before this agent instance started interacting with the thread.
        It handles pagination to ensure all messages are captured.
        """
        # Retrieve all initial message IDs
        initial_message_ids: Set[str] = set()
        after: str | None = None
        while True:
            msgs: models.OpenAIPageableListOfThreadMessage = await self._project_client.agents.list_messages(
                thread_id=self.thread_id, after=after, order=models.ListSortOrder.ASCENDING, limit=100
            )

            for msg in msgs.data:
                initial_message_ids.add(msg.id)
            if not msgs.has_more:
                break
            after = msgs.data[-1].id
        self._initial_message_ids = initial_message_ids

    async def _execute_tool_call(self, tool_call: FunctionCall, cancellation_token: CancellationToken) -> str:
        """
        Execute a tool call requested by the Azure AI agent.

        Args:
            tool_call (FunctionCall): The function call information including name and arguments
            cancellation_token (CancellationToken): Token for cancellation handling

        Returns:
            str: The string representation of the tool call result

        Raises:
            ValueError: If the requested tool is not available or no tools are registered
        """
        if not self._original_tools:
            raise ValueError("No tools are available.")
        tool = next((t for t in self._original_tools if t.name == tool_call.name), None)
        if tool is None:
            raise ValueError(f"The tool '{tool_call.name}' is not available.")
        arguments = json.loads(tool_call.arguments)
        result = await tool.run_json(arguments, cancellation_token)
        return tool.return_value_as_string(result)

    async def _upload_files(
        self,
        file_paths: str | Iterable[str],
        purpose: str = "assistant",
        sleep_interval: float = 0.5,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> List[str]:
        """
        Upload files to the Azure AI Assistant API.

        This method handles uploading one or more files to be used by the agent
        and tracks their IDs in the agent's state.

        Args:
            file_paths (str | Iterable[str]): Path(s) to file(s) to upload
            purpose (str): The purpose of the file, defaults to "assistant"
            sleep_interval (float): Time to sleep between polling for file status
            cancellation_token (Optional[CancellationToken]): Token for cancellation handling

        Returns:
            List[str]: List of file IDs for the uploaded files

        Raises:
            ValueError: If file upload fails
        """
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        await self._ensure_initialized()

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        file_ids: List[str] = []
        for file_path in file_paths:
            file_name = os.path.basename(file_path)

            file: models.OpenAIFile = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.upload_file_and_poll(
                        file_path=file_path, purpose=purpose, sleep_interval=sleep_interval
                    )
                )
            )

            if file.status != models.FileState.PROCESSED:
                raise ValueError(f"File upload failed with status {file.status}")

            event_logger.debug(f"File uploaded successfully: {file.id}, {file_name}")

            file_ids.append(file.id)
            self._uploaded_file_ids.append(file.id)

        return file_ids

    # Public Methods
    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: Optional[CancellationToken] = None,
        message_limit: int = 1,
    ) -> Response:
        """
        Process incoming messages and return a response from the Azure AI agent.

        This method is the primary entry point for interaction with the agent.
        It delegates to on_messages_stream and returns the final response.

        Args:
            messages (Sequence[ChatMessage]): The messages to process
            cancellation_token (CancellationToken): Token for cancellation handling
            message_limit (int, optional): Maximum number of messages to retrieve from the thread

        Returns:
            Response: The agent's response, including the chat message and any inner events

        Raises:
            AssertionError: If the stream doesn't return a final result
        """
        async for message in self.on_messages_stream(
            messages=messages, cancellation_token=cancellation_token, message_limit=message_limit
        ):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

        async def on_messages_stream(
            self,
            messages: Sequence[ChatMessage],
            message_limit: int = 1,
            cancellation_token: CancellationToken = None,
            sleep_interval: float = 0.5,
        ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
            """
            Process incoming messages and yield streaming responses from the Azure AI agent.
    
            This method handles the complete interaction flow with the Azure AI agent:
            1. Processing input messages
            2. Creating and monitoring a run
            3. Handling tool calls and their results
            4. Retrieving and returning the agent's final response
    
            The method yields events during processing (like tool calls) and finally yields
            the complete Response with the agent's message.
    
            Args:
                messages (Sequence[ChatMessage]): The messages to process
                message_limit (int, optional): Maximum number of messages to retrieve from the thread
                cancellation_token (CancellationToken, optional): Token for cancellation handling
                sleep_interval (float, optional): Time to sleep between polling for run status
    
            Yields:
                AgentEvent | ChatMessage | Response: Events during processing and the final response
    
            Raises:
                ValueError: If the run fails or no message is received from the assistant
            """
            if cancellation_token is None:
                cancellation_token = CancellationToken()
    
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
                if run.status == models.RunStatus.REQUIRES_ACTION and run.required_action is not None:
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
                                tool_outputs=[
                                    models.ToolOutput(tool_call_id=t.call_id, output=t.content) for t in tool_outputs
                                ],
                            )
                        )
                    )
                    continue
    
                if run.status == models.RunStatus.COMPLETED:
                    break
    
                # TODO support for parameter to control polling interval
                await asyncio.sleep(sleep_interval)
    
            # After run is completed, get the messages
            event_logger.debug("Retrieving messages from thread")
            agent_messages: models.OpenAIPageableListOfThreadMessage = await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.list_messages(
                        thread_id=self._thread_id, order=models.ListSortOrder.DESCENDING, limit=message_limit
                    )
                )
            )
    
            if not agent_messages.data:
                raise ValueError("No messages received from assistant")
                
            # Get the last message from the agent
            last_message = agent_messages.get_last_message_by_role(models.MessageRole.AGENT)
            if not last_message:
                event_logger.debug("No message with AGENT role found, falling back to first message")
                last_message = agent_messages.data[0]  # Fallback to first message
                
            if not last_message.content:
                raise ValueError(f"No content in the last message")
    
            # Extract text content
            message_text = ""
            for text_message in last_message.text_messages:
                message_text += text_message.text.value
    
            # Extract citations
            citations = []
            
            # Try accessing annotations directly
            if hasattr(last_message, 'annotations') and last_message.annotations:
                event_logger.debug(f"Found {len(last_message.annotations)} annotations")
                for annotation in last_message.annotations:
                    if hasattr(annotation, 'url_citation'):
                        event_logger.debug(f"Citation found: {annotation.url_citation.url}")
                        citations.append({
                            "url": annotation.url_citation.url,
                            "title": annotation.url_citation.title,
                            "text": None
                        })
            
            # For backwards compatibility
            elif hasattr(last_message, 'url_citation_annotations') and last_message.url_citation_annotations:
                event_logger.debug(f"Found {len(last_message.url_citation_annotations)} URL citations")
                for annotation in last_message.url_citation_annotations:
                    citations.append({
                        "url": annotation.url_citation.url,
                        "title": annotation.url_citation.title,
                        "text": None
                    })
            
            event_logger.debug(f"Total citations extracted: {len(citations)}")
            
            # Create the response message with citations as JSON string
            chat_message = TextMessage(
                source=self.name, 
                content=message_text,
                metadata={"citations": json.dumps(citations)} if citations else {}
            )
    
            # Return the assistant's response as a Response with inner messages
            yield Response(chat_message=chat_message, inner_messages=inner_messages)

    async def handle_text_message(self, content: str, cancellation_token: Optional[CancellationToken] = None) -> None:
        """
        Handle a text message by adding it to the conversation thread.

        Args:
            content (str): The text content of the message
            cancellation_token (CancellationToken): Token for cancellation handling

        Returns:
            None
        """

        if cancellation_token is None:
            cancellation_token = CancellationToken()

        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.create_message(
                    thread_id=self.thread_id,
                    content=content,
                    role=models.MessageRole.USER,
                )
            )
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """
        Reset the agent's conversation by creating a new thread.

        This method allows for resetting a conversation without losing the agent
        definition or capabilities. It creates a new thread for fresh conversations.

        Note: Currently the Azure AI Agent API has no support for deleting messages,
        so a new thread is created instead.

        Args:
            cancellation_token (CancellationToken): Token for cancellation handling
        """
        # This will enforce the creation of a new thread
        await self._ensure_initialized(create_new_thread=True)

    async def save_state(self) -> Mapping[str, Any]:
        """
        Save the current state of the agent for future restoration.

        This method serializes the agent's state including IDs for the agent, thread,
        messages, and associated resources like vector stores and uploaded files.

        Returns:
            Mapping[str, Any]: A dictionary containing the serialized state data
        """
        state = AzureAIAgentState(
            agent_id=self._agent.id if self._agent else self._agent_id,
            thread_id=self._thread.id if self._thread else self._init_thread_id,
            initial_message_ids=list(self._initial_message_ids),
            vector_store_id=self._vector_store_id,
            uploaded_file_ids=self._uploaded_file_ids,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """
        Load a previously saved state into this agent.

        This method deserializes and restores a previously saved agent state,
        setting up the agent to continue a previous conversation or session.

        Args:
            state (Mapping[str, Any]): The previously saved state dictionary
        """
        agent_state = AzureAIAgentState.model_validate(state)
        self._agent_id = agent_state.agent_id
        self._init_thread_id = agent_state.thread_id
        self._initial_message_ids = set(agent_state.initial_message_ids)
        self._vector_store_id = agent_state.vector_store_id
        self._uploaded_file_ids = agent_state.uploaded_file_ids

    async def on_upload_for_code_interpreter(
        self,
        file_paths: str | Iterable[str],
        cancellation_token: Optional[CancellationToken] = None,
        sleep_interval: float = 0.5,
    ) -> None:
        """
        Upload files to be used with the code interpreter tool.

        This method uploads files for the agent's code interpreter tool and
        updates the thread's tool resources to include these files.

        Args:
            file_paths (str | Iterable[str]): Path(s) to file(s) to upload
            cancellation_token (Optional[CancellationToken]): Token for cancellation handling
            sleep_interval (float): Time to sleep between polling for file status

        Raises:
            ValueError: If file upload fails or the agent doesn't have code interpreter capability
        """
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        await self._ensure_initialized()

        file_ids = await self._upload_files(
            file_paths=file_paths,
            cancellation_token=cancellation_token,
            sleep_interval=sleep_interval,
            purpose=models.FilePurpose.AGENTS,
        )

        # Update thread with the new files
        thread: models.AgentThread = await cancellation_token.link_future(
            asyncio.ensure_future(self._project_client.agents.get_thread(thread_id=self.thread_id))
        )

        tool_resources: models.ToolResources = thread.tool_resources or models.ToolResources()
        code_interpreter_resource = tool_resources.code_interpreter or models.CodeInterpreterToolResource()
        existing_file_ids: List[str] = code_interpreter_resource.file_ids or []
        existing_file_ids.extend(file_ids)

        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.update_thread(
                    thread_id=self.thread_id,
                    tool_resources=models.ToolResources(
                        code_interpreter=models.CodeInterpreterToolResource(file_ids=existing_file_ids)
                    ),
                )
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
        """
        Upload files to be used with the file search tool.

        This method handles uploading files for the file search capability, creating a vector
        store if necessary, and updating the agent's configuration to use the vector store.

        Args:
            file_paths (str | Iterable[str]): Path(s) to file(s) to upload
            cancellation_token (CancellationToken): Token for cancellation handling
            vector_store_name (Optional[str]): Name to assign to the vector store if creating a new one
            data_sources (Optional[List[models.VectorStoreDataSource]]): Additional data sources for the vector store
            expires_after (Optional[models.VectorStoreExpirationPolicy]): Expiration policy for vector store content
            chunking_strategy (Optional[models.VectorStoreChunkingStrategyRequest]): Strategy for chunking file content
            vector_store_metadata (Optional[Dict[str, str]]): Additional metadata for the vector store
            vector_store_polling_sleep_interval (float): Time to sleep between polling for vector store status

        Raises:
            ValueError: If file search is not enabled for this agent or file upload fails
        """
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
                    self._project_client.agents.create_vector_store_and_poll(
                        file_ids=[],
                        name=vector_store_name,
                        data_sources=data_sources,
                        expires_after=expires_after,
                        chunking_strategy=chunking_strategy,
                        metadata=vector_store_metadata,
                        sleep_interval=vector_store_polling_sleep_interval,
                    )
                )
            )
            self._vector_store_id = vector_store.id

            # Update assistant with vector store ID
            await cancellation_token.link_future(
                asyncio.ensure_future(
                    self._project_client.agents.update_agent(
                        agent_id=self._get_agent_id,
                        tools=self._api_tools,
                        tool_resources=models.ToolResources(
                            file_search=models.FileSearchToolResource(vector_store_ids=[self._vector_store_id])
                        ),
                    )
                )
            )

        file_ids = await self._upload_files(
            file_paths=file_paths, cancellation_token=cancellation_token, purpose=models.FilePurpose.AGENTS
        )

        # Create file batch with the file IDs
        await cancellation_token.link_future(
            asyncio.ensure_future(
                self._project_client.agents.create_vector_store_file_batch_and_poll(
                    vector_store_id=self._vector_store_id, file_ids=file_ids
                )
            )
        )


if __name__ == "__main__":
    # Example usage of AzureAIAgent
    # Replace with your actual connection string and credentials
    """
        TODO:
        [X] Support for file upload
        [] Support for sharepoint grounding
        [] Support for azure function grounding
        [X] Support for file search
        [X] Support for custom function calling
        [X] Add metadata to the thread (agent_id, source ="AUTODGEN_AGENT")
    """
