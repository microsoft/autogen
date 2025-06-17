import asyncio
import json
import logging
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypedDict,
    Union,
    cast,
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
    ToolCallSummaryMessage,
)
from autogen_core import CancellationToken, Component, ComponentModel, FunctionCall
from autogen_core.models import UserMessage
from autogen_core.tools import Tool
from pydantic import BaseModel, Field

from openai import AsyncAzureOpenAI, AsyncOpenAI

# Number of characters to display when previewing image content in logs and UI
# Base64 encoded images can be very long, so we truncate for readability
IMAGE_CONTENT_PREVIEW_LENGTH = 50

# NOTE: We use the new Responses API, so ChatCompletion imports are not needed.

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


def _convert_tool_to_function_schema(tool: Tool) -> Dict[str, Any]:
    schema = tool.schema
    parameters: Dict[str, object] = {}
    if "parameters" in schema:
        parameters = {
            "type": schema["parameters"]["type"],
            "properties": schema["parameters"]["properties"],
        }
        if "required" in schema["parameters"]:
            parameters["required"] = schema["parameters"]["required"]

    return {
        "name": schema["name"],
        "description": schema.get("description", ""),
        "parameters": parameters,
    }


class OpenAIMessageContent(TypedDict):
    type: str
    text: str


class OpenAIImageUrlContent(TypedDict):
    url: str


class OpenAIImageContent(TypedDict):
    type: str
    image_url: OpenAIImageUrlContent


class OpenAIMessage(TypedDict):
    role: str
    content: Union[str, List[Union[OpenAIMessageContent, OpenAIImageContent]]]


def _convert_message_to_openai_message(
    message: Union[TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage],
) -> OpenAIMessage:
    """Convert an AutoGen message to an OpenAI message format."""
    if isinstance(message, TextMessage):
        if message.source == "user":
            return {"role": "user", "content": str(message.content)}
        elif message.source == "system":
            return {"role": "system", "content": str(message.content)}
        elif message.source == "assistant":
            return {"role": "assistant", "content": str(message.content)}
        else:
            return {"role": "user", "content": str(message.content)}
    elif isinstance(message, MultiModalMessage):
        content_parts: List[Union[OpenAIMessageContent, OpenAIImageContent]] = []
        for part in message.content:
            if isinstance(part, TextMessage):
                content_parts.append({"type": "text", "text": str(part.content)})
            elif isinstance(part, ImageMessage):
                image_content = str(part.content)
                content_parts.append({"type": "image_url", "image_url": {"url": image_content}})
        return {"role": "user", "content": content_parts}
    else:
        return {"role": "user", "content": str(message.content)}


class OpenAIAgentState(BaseModel):
    type: str = Field(default="OpenAIAgentState")
    response_id: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class OpenAIAgentConfig(BaseModel):
    name: str
    description: str
    model: str
    instructions: str
    tools: List[ComponentModel] | None = None
    temperature: Optional[float] = 1
    max_output_tokens: Optional[int] = None
    json_mode: bool = False
    store: bool = True
    truncation: str = "disabled"


class FunctionExecutionResult(BaseModel):
    """Result of a function execution."""

    content: str
    call_id: str
    name: str
    is_error: bool = False


class OpenAIAgent(BaseChatAgent, Component[OpenAIAgentConfig]):
    """
    An agent implementation that uses the OpenAI Responses API to generate responses.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[openai]"
        # pip install "autogen-ext[openai,azure]"  # For Azure OpenAI Assistant

    This agent leverages the Responses API to generate responses with capabilities like:

    * Custom function calling
    * Multi-turn conversations
    * Built-in tool support (file_search, code_interpreter, web_search_preview, etc.)

    Args:
        name (str): Name of the agent
        description (str): Description of the agent's purpose
        client (Union[AsyncOpenAI, AsyncAzureOpenAI]): OpenAI client instance
        model (str): Model to use (e.g. "gpt-4.1")
        instructions (str): System instructions for the agent
        tools (Optional[Iterable[Union[str, Tool]]]): Tools the agent can use.
            Supported string values: "file_search", "code_interpreter", "web_search_preview",
            "computer_use_preview", "image_generation", "mcp".
            Also accepts custom Tool objects for function calling.
        temperature (Optional[float]): Temperature for response generation (default: 1)
        max_output_tokens (Optional[int]): Maximum output tokens
        json_mode (bool): Whether to use JSON mode (default: False)
        store (bool): Whether to store conversations (default: True)
        truncation (str): Truncation strategy (default: "disabled")

    Example:

        .. code-block:: python

            from openai import AsyncOpenAI
            from autogen_core import CancellationToken
            from autogen_ext.agents.openai import OpenAIAgent
            from autogen_agentchat.messages import TextMessage


            async def example():
                cancellation_token = CancellationToken()
                client = AsyncOpenAI()
                agent = OpenAIAgent(
                    name="Simple Agent",
                    description="A simple OpenAI agent using the Responses API",
                    client=client,
                    model="gpt-4.1",
                    instructions="You are a helpful assistant.",
                    tools=["web_search_preview", "code_interpreter"],
                )
                response = await agent.on_messages([TextMessage(source="user", content="Hello!")], cancellation_token)
                print(response)

        asyncio.run(example())

    .. versionchanged:: v0.4.1

       Added support for built-in tool types like file_search, web_search_preview,
       code_interpreter, computer_use_preview, image_generation, and mcp.

    """

    component_config_schema = OpenAIAgentConfig
    component_provider_override = "autogen_ext.agents.openai.OpenAIAgent"

    def __init__(
        self: "OpenAIAgent",
        name: str,
        description: str,
        client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        model: str,
        instructions: str,
        tools: Optional[
            Iterable[
                Union[
                    Literal[
                        "file_search",
                        "code_interpreter",
                        "web_search_preview",
                        "computer_use_preview",
                        "image_generation",
                        "mcp",
                    ],
                    Tool,
                ]
            ]
        ] = None,
        temperature: Optional[float] = 1,
        max_output_tokens: Optional[int] = None,
        json_mode: bool = False,
        store: bool = True,
        truncation: str = "disabled",
    ) -> None:
        super().__init__(name, description)
        self._client: Union[AsyncOpenAI, AsyncAzureOpenAI] = client
        self._model: str = model
        self._instructions: str = instructions
        self._temperature: Optional[float] = temperature
        self._max_output_tokens: Optional[int] = max_output_tokens
        self._json_mode: bool = json_mode
        self._store: bool = store
        self._truncation: str = truncation
        self._last_response_id: Optional[str] = None
        self._message_history: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._tool_map: Dict[str, Tool] = {}
        if tools is not None:
            for tool in tools:
                if isinstance(tool, str):
                    # Handle built-in tool types
                    if tool == "file_search":
                        self._tools.append({"type": "file_search"})
                    elif tool == "code_interpreter":
                        self._tools.append({"type": "code_interpreter"})
                    elif tool == "web_search_preview":
                        self._tools.append({"type": "web_search_preview"})
                    elif tool == "computer_use_preview":
                        self._tools.append({"type": "computer_use_preview"})
                    elif tool == "image_generation":
                        self._tools.append({"type": "image_generation"})
                    elif tool == "mcp":
                        self._tools.append({"type": "mcp"})
                    else:
                        raise ValueError(f"Unsupported built-in tool type: {tool}")
                elif isinstance(tool, Tool):
                    # Handle custom function tools
                    function_schema: Dict[str, Any] = {
                        "type": "function",
                        "function": _convert_tool_to_function_schema(tool),
                    }
                    self._tools.append(function_schema)
                    self._tool_map[tool.name] = tool
                else:
                    raise ValueError(f"Unsupported tool type: {type(tool)}")

    def _convert_message_to_dict(self, message: OpenAIMessage) -> Dict[str, Any]:
        """Convert an OpenAIMessage to a Dict[str, Any]."""
        return dict(message)

    async def list_assistants(
        self: "OpenAIAgent",
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: Optional[int] = 20,
        order: Optional[str] = "desc",
    ) -> Dict[str, Any]:  # noqa: D102
        """
        List all assistants using the OpenAI API.

        Args:
            after (Optional[str]): Cursor for pagination (fetch after this assistant ID).
            before (Optional[str]): Cursor for pagination (fetch before this assistant ID).
            limit (Optional[int]): Number of assistants to return (1-100, default 20).
            order (Optional[str]): 'asc' or 'desc' by created_at (default 'desc').

        Returns:
            Dict[str, Any]: The OpenAI API response containing:
                    - object: 'list'
                    - data: List of assistant objects
                    - first_id: str
                    - last_id: str
                    - has_more: bool

        Example:
            .. code-block:: python

                import asyncio
                from typing import Dict, Any
                from autogen_ext.agents.openai import OpenAIAgent
                from openai import AsyncOpenAI


                async def example() -> None:
                    client = AsyncOpenAI()
                    agent = OpenAIAgent(
                        name="test_agent",
                        description="Test agent",
                        client=client,
                        model="gpt-4",
                        instructions="You are a helpful assistant.",
                    )
                    assistants: Dict[str, Any] = await agent.list_assistants(limit=5)
                    print(assistants)


                asyncio.run(example())

        """
        params = {"limit": limit, "order": order}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if hasattr(self._client, "assistants"):
            client_any = cast(Any, self._client)
            response = await client_any.assistants.list(**params)
            if hasattr(response, "model_dump"):
                return cast(Dict[str, Any], response.model_dump())
            return cast(Dict[str, Any], dict(response))
        else:
            raise NotImplementedError("The OpenAI client does not support listing assistants.")

    async def retrieve_assistant(self: "OpenAIAgent", assistant_id: str) -> Dict[str, Any]:  # noqa: D102
        """
        Retrieve a single assistant by its ID using the OpenAI API.

        Args:
            assistant_id (str): The ID of the assistant to retrieve.

        Returns:
            Dict[str, Any]: The assistant object.

        Example:
            .. code-block:: python

                import asyncio
                from typing import Dict, Any
                from autogen_ext.agents.openai import OpenAIAgent
                from openai import AsyncOpenAI


                async def example() -> None:
                    client = AsyncOpenAI()
                    agent = OpenAIAgent(
                        name="test_agent",
                        description="Test agent",
                        client=client,
                        model="gpt-4",
                        instructions="You are a helpful assistant.",
                    )
                    assistant: Dict[str, Any] = await agent.retrieve_assistant("asst_abc123")
                    print(assistant)


                asyncio.run(example())

        """
        if hasattr(self._client, "assistants"):
            client_any = cast(Any, self._client)
            response = await client_any.assistants.retrieve(assistant_id=assistant_id)
            if hasattr(response, "model_dump"):
                return cast(Dict[str, Any], response.model_dump())
            return cast(Dict[str, Any], dict(response))
        else:
            raise NotImplementedError("The OpenAI client does not support retrieving assistants.")

    async def modify_assistant(
        self: "OpenAIAgent",
        assistant_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Any]] = None,
        top_p: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:  # noqa: D102
        """
        Modify (update) an assistant by its ID using the OpenAI API.

        Args:
            assistant_id (str): The ID of the assistant to update.
            name (Optional[str]): New name for the assistant.
            description (Optional[str]): New description.
            instructions (Optional[str]): New instructions.
            metadata (Optional[dict]): New metadata.
            model (Optional[str]): New model.
            reasoning_effort (Optional[str]): New reasoning effort.
            response_format (Optional[str]): New response format.
            temperature (Optional[float]): New temperature.
            tool_resources (Optional[dict]): New tool resources.
            tools (Optional[list]): New tools.
            top_p (Optional[float]): New top_p value.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, Any]: The updated assistant object.

        Example:
            .. code-block:: python

                import asyncio
                from typing import Dict, Any
                from autogen_ext.agents.openai import OpenAIAgent
                from openai import AsyncOpenAI


                async def example() -> None:
                    client = AsyncOpenAI()
                    agent = OpenAIAgent(
                        name="test_agent",
                        description="Test agent",
                        client=client,
                        model="gpt-4",
                        instructions="You are a helpful assistant.",
                    )
                    updated: Dict[str, Any] = await agent.modify_assistant(
                        assistant_id="asst_123",
                        instructions="You are an HR bot, and you have access to files to answer employee questions about company policies. Always response with info from either of the files.",
                        tools=[{"type": "file_search"}],
                        tool_resources={"file_search": {"vector_store_ids": []}},
                    )
                    print(updated)


                asyncio.run(example())

        """
        params = {k: v for k, v in locals().items() if k not in {"self", "assistant_id", "kwargs"} and v is not None}
        params.update(kwargs)
        if hasattr(self._client, "assistants"):
            client_any = cast(Any, self._client)
            response = await client_any.assistants.update(assistant_id=assistant_id, **params)
            if hasattr(response, "model_dump"):
                return cast(Dict[str, Any], response.model_dump())
            return cast(Dict[str, Any], dict(response))
        else:
            raise NotImplementedError("The OpenAI client does not support modifying assistants.")

    async def delete_assistant(self: "OpenAIAgent", assistant_id: str) -> Dict[str, Any]:  # noqa: D102
        """
        Delete an assistant by its ID using the OpenAI API.

        Args:
            assistant_id (str): The ID of the assistant to delete.

        Returns:
            Dict[str, Any]: The deletion status object (e.g., {"id": ..., "object": "assistant.deleted", "deleted": true}).

        Example:
            .. code-block:: python

                import asyncio
                from typing import Dict, Any
                from autogen_ext.agents.openai import OpenAIAgent
                from openai import AsyncOpenAI


                async def example() -> None:
                    client = AsyncOpenAI()
                    agent = OpenAIAgent(
                        name="test_agent",
                        description="Test agent",
                        client=client,
                        model="gpt-4",
                        instructions="You are a helpful assistant.",
                    )
                    result: Dict[str, Any] = await agent.delete_assistant("asst_abc123")
                    print(result)


                asyncio.run(example())

        """
        if hasattr(self._client, "assistants"):
            client_any = cast(Any, self._client)
            response = await client_any.assistants.delete(assistant_id=assistant_id)
            if hasattr(response, "model_dump"):
                return cast(Dict[str, Any], response.model_dump())
            return cast(Dict[str, Any], dict(response))
        else:
            raise NotImplementedError("The OpenAI client does not support deleting assistants.")

    @property
    def produced_message_types(
        self: "OpenAIAgent",
    ) -> Sequence[
        Union[
            Type[TextMessage],
            Type[MultiModalMessage],
            Type[StopMessage],
            Type[ToolCallSummaryMessage],
            Type[HandoffMessage],
        ]
    ]:
        """Return the types of messages that this agent can produce."""
        return [TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage]

    async def _execute_tool_call(
        self: "OpenAIAgent", tool_call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        tool_name = tool_call.name
        if tool_name not in self._tool_map:
            return FunctionExecutionResult(
                content=f"Error: Tool '{tool_name}' is not available",
                call_id=tool_call.id,
                name=tool_name,
                is_error=True,
            )

        tool = self._tool_map[tool_name]
        try:
            try:
                arguments = json.loads(tool_call.arguments)
            except json.JSONDecodeError as json_err:
                return FunctionExecutionResult(
                    content=f"Error: Invalid JSON in tool arguments - {str(json_err)}",
                    call_id=tool_call.id,
                    name=tool_name,
                    is_error=True,
                )

            result = await tool.run_json(arguments, cancellation_token, call_id=tool_call.id)
            return FunctionExecutionResult(
                content=tool.return_value_as_string(result), call_id=tool_call.id, name=tool_name, is_error=False
            )
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            event_logger.warning(f"Tool execution error in {tool_name}: {error_msg}")
            return FunctionExecutionResult(content=error_msg, call_id=tool_call.id, name=tool_name, is_error=True)

    def _build_api_parameters(self: "OpenAIAgent", messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        has_system_message = any(msg.get("role") == "system" for msg in messages)
        if self._instructions and not has_system_message:
            messages = [{"role": "system", "content": self._instructions}] + messages
        api_params: Dict[str, Any] = {
            "model": self._model,
            "input": messages,  # Responses API expects 'input'
        }
        if self._temperature is not None:
            api_params["temperature"] = self._temperature
        if self._max_output_tokens is not None:
            api_params["max_output_tokens"] = self._max_output_tokens
        if self._tools:
            api_params["tools"] = self._tools
        if self._json_mode:
            api_params["text"] = {"type": "json_object"}
        api_params["store"] = self._store
        api_params["truncation"] = self._truncation
        if self._last_response_id:
            api_params["previous_response_id"] = self._last_response_id
        return api_params

    async def on_messages(
        self: "OpenAIAgent", messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        response = None
        inner_messages: List[
            Union[AgentEvent, TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage]
        ] = []

        async for msg in self.on_messages_stream(messages, cancellation_token):
            if isinstance(msg, Response):
                response = msg
            # ModelClientStreamingChunkEvent does not exist in this version, so skip this check
            else:
                inner_messages.append(msg)

        if response is None:
            raise ValueError("No response was generated")

        if response.inner_messages is None:
            response.inner_messages = []

        for msg in inner_messages:
            if msg not in response.inner_messages:
                response.inner_messages = list(response.inner_messages) + [msg]

        return response

    async def on_messages_stream(
        self: "OpenAIAgent", messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[
        Union[
            AgentEvent, TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage, Response
        ],
        None,
    ]:
        input_messages: List[Dict[str, Any]] = []

        if self._message_history:
            input_messages.extend(self._message_history)

        for message in messages:
            if isinstance(
                message, (TextMessage, MultiModalMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage)
            ):
                openai_message = _convert_message_to_openai_message(message)
                dict_message = self._convert_message_to_dict(openai_message)
                input_messages.append(dict_message)
                self._message_history.append(dict_message)
            else:
                msg_content = str(cast(Any, message).content) if hasattr(message, "content") else str(message)
                dict_message = {"role": "user", "content": msg_content}
                input_messages.append(dict_message)
                self._message_history.append(dict_message)

        inner_messages: List[AgentEvent | ChatMessage] = []

        api_params = self._build_api_parameters(input_messages)

        try:
            client = cast(Any, self._client)
            response_obj = await cancellation_token.link_future(
                asyncio.ensure_future(client.responses.create(**api_params))
            )
            content = getattr(response_obj, "output_text", None)
            response_id = getattr(response_obj, "id", None)
            self._last_response_id = response_id
            self._message_history.append({"role": "assistant", "content": str(content) if content is not None else ""})
            final_message = TextMessage(source=self.name, content=str(content) if content is not None else "")
            response = Response(chat_message=final_message, inner_messages=inner_messages)
            yield response
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            event_logger.error(f"API error: {error_message}", exc_info=True)
            error_response = TextMessage(source=self.name, content=error_message)
            yield Response(chat_message=error_response, inner_messages=inner_messages)

    async def on_reset(self: "OpenAIAgent", cancellation_token: CancellationToken) -> None:
        self._last_response_id = None
        self._message_history = []

    async def save_state(self: "OpenAIAgent") -> Mapping[str, Any]:
        state = OpenAIAgentState(
            response_id=self._last_response_id,
            history=self._message_history,
        )
        return state.model_dump()

    async def load_state(self: "OpenAIAgent", state: Mapping[str, Any]) -> None:
        agent_state = OpenAIAgentState.model_validate(state)
        self._last_response_id = agent_state.response_id
        self._message_history = agent_state.history

    def _to_config(self: "OpenAIAgent") -> OpenAIAgentConfig:
        """Convert the OpenAI agent to a declarative config."""
        tool_configs: List[Dict[str, Any]] = []
        for tool in self._tool_map.values():
            try:
                if hasattr(tool, "dump_component"):
                    tool_any = cast(Any, tool)
                    component_dict = tool_any.dump_component()
                    tool_configs.append(component_dict)
                else:
                    tool_configs.append(
                        {
                            "provider": "autogen_core.tools.FunctionTool",
                            "config": {
                                "name": tool.name,
                                "description": getattr(tool, "description", ""),
                            },
                        }
                    )
            except Exception as e:
                warnings.warn(f"Error serializing tool: {e}", stacklevel=2)
                tool_configs.append(
                    {
                        "provider": "autogen_core.tools.FunctionTool",
                        "config": {
                            "name": getattr(tool, "name", "unknown_tool"),
                            "description": getattr(tool, "description", ""),
                        },
                    }
                )
        return OpenAIAgentConfig(
            name=self.name,
            description=self.description,
            model=self._model,
            instructions=self._instructions,
            tools=cast(List[ComponentModel], tool_configs),
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            json_mode=self._json_mode,
            store=self._store,
            truncation=self._truncation,
        )

    @classmethod
    def _from_config(cls: Type["OpenAIAgent"], config: OpenAIAgentConfig) -> "OpenAIAgent":
        """Create an OpenAI agent from a declarative config."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        tools: Optional[List[Tool]] = None
        if config.tools:
            tools_list: List[Tool] = []
            for tool_config in config.tools:
                try:
                    provider = tool_config.provider
                    module_name, class_name = provider.rsplit(".", 1)
                    module = __import__(module_name, fromlist=[class_name])
                    tool_cls = getattr(module, class_name)
                    tool = tool_cls(**tool_config.config)
                    tools_list.append(cast(Tool, tool))
                except Exception as e:
                    warnings.warn(f"Error loading tool: {e}", stacklevel=2)
                    from autogen_core.tools import FunctionTool

                    async def dummy_func(*args: Any, **kwargs: Any) -> str:
                        return "Tool not fully restored"

                    tool = FunctionTool(
                        name=tool_config.config.get("name", "unknown_tool"),
                        description=tool_config.config.get("description", ""),
                        func=dummy_func,
                    )
                    tools_list.append(tool)
            tools = tools_list

        return cls(
            name=config.name,
            description=config.description,
            client=client,
            model=config.model,
            instructions=config.instructions,
            tools=tools,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            json_mode=config.json_mode,
            store=config.store,
            truncation=config.truncation,
        )


# Define our own ImageMessage since it's not available
class ImageMessage(BaseChatMessage):
    """A message containing an image."""

    content: str  # URL or base64 string

    def to_model_message(self) -> UserMessage:
        return UserMessage(content=self.content, source=self.source)

    def to_model_text(self) -> str:
        return "[image]"

    def to_text(self) -> str:
        # Truncate long image content (especially base64) for better readability
        # While still showing enough of the URL or content to be identifiable
        if len(self.content) > IMAGE_CONTENT_PREVIEW_LENGTH:
            return f"[Image: {self.content[:IMAGE_CONTENT_PREVIEW_LENGTH]}...]"
        return f"[Image: {self.content}]"
