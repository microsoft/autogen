import asyncio
import logging
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
from autogen_core import CancellationToken, Component
from autogen_core.models import UserMessage
from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict

from openai import AsyncAzureOpenAI, AsyncOpenAI  # type: ignore

# Number of characters to display when previewing image content in logs and UI
# Base64 encoded images can be very long, so we truncate for readability
IMAGE_CONTENT_PREVIEW_LENGTH = 50

# NOTE: We use the new Responses API, so ChatCompletion imports are not needed.

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


# TypedDict classes for built-in tool configurations
class FileSearchToolConfig(TypedDict):
    """Configuration for file_search tool."""

    type: Literal["file_search"]
    vector_store_ids: List[str]  # required - The IDs of the vector stores to search
    max_num_results: NotRequired[int]  # optional
    ranking_options: NotRequired[Dict[str, Any]]  # optional
    filters: NotRequired[Dict[str, Any]]  # optional


class WebSearchToolConfig(TypedDict):
    """Configuration for web_search_preview tool."""

    type: Literal["web_search_preview"]
    search_context_size: NotRequired[str]  # optional
    user_location: NotRequired[Union[str, Dict[str, Any]]]  # optional - Can be string or structured location


class ComputerUseToolConfig(TypedDict):
    """Configuration for computer_use_preview tool."""

    type: Literal["computer_use_preview"]
    display_height: int  # required - Display height in pixels
    display_width: int  # required - Display width in pixels
    environment: str  # required - Environment type for computer use


class MCPToolConfig(TypedDict):
    """Configuration for mcp tool."""

    type: Literal["mcp"]
    server_label: str  # required - Label for the MCP server
    server_url: str  # required - URL of the MCP server
    allowed_tools: NotRequired[List[str]]  # optional - List of allowed tools
    headers: NotRequired[Dict[str, str]]  # optional - HTTP headers for requests
    require_approval: NotRequired[bool]  # optional - Whether to require user approval


class CodeInterpreterToolConfig(TypedDict):
    """Configuration for code_interpreter tool."""

    type: Literal["code_interpreter"]
    container: str | Dict[str, Any]  # required - Container configuration for code execution


class ImageGenerationToolConfig(TypedDict):
    """Configuration for image_generation tool."""

    type: Literal["image_generation"]
    background: NotRequired[str]  # optional - Background color or image
    input_image_mask: NotRequired[str]  # optional - Mask for input image editing


class LocalShellToolConfig(TypedDict):
    """Configuration for local_shell tool.

    WARNING: This tool is only supported with the 'codex-mini-latest' model
    and is available exclusively through the Responses API.
    """

    type: Literal["local_shell"]
    # Note: local_shell currently has no additional parameters in the API


# Union type for all built-in tool configurations
BuiltinToolConfig = Union[
    FileSearchToolConfig,
    WebSearchToolConfig,
    ComputerUseToolConfig,
    MCPToolConfig,
    CodeInterpreterToolConfig,
    ImageGenerationToolConfig,
    LocalShellToolConfig,
]


# Define ImageMessage class early since it's used in _convert_message_to_openai_message
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
    """
    Configuration model for OpenAI agent supporting OpenAI built-in tools only.

    .. versionchanged:: v0.7.0
        Added support for built-in tools in JSON configuration via _to_config and _from_config methods.
        The tools field accepts built-in tool configurations (dict format) and built-in tool names (string format).
        Custom tools are not supported.
    """

    name: str
    description: str
    model: str
    instructions: str
    tools: List[Dict[str, Any] | str] | None = None
    temperature: Optional[float] = 1
    max_output_tokens: Optional[int] = None
    json_mode: bool = False
    store: bool = True
    truncation: str = "disabled"


class OpenAIAgent(BaseChatAgent, Component[OpenAIAgentConfig]):
    """
    An agent implementation that uses the OpenAI Responses API to generate responses.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[openai]"
        # pip install "autogen-ext[openai,azure]"  # For Azure OpenAI Assistant

    This agent leverages the Responses API to generate responses with capabilities like:

    * Multi-turn conversations
    * Built-in tool support (file_search, code_interpreter, web_search_preview, etc.)

    Currently, custom tools are not supported.

    .. versionchanged:: v0.7.0

        Added support for built-in tool types like file_search, web_search_preview,
        code_interpreter, computer_use_preview, image_generation, and mcp.
        Added support for tool configurations with required and optional parameters.

    Built-in tools are split into two categories:

    **Tools that can use string format** (no required parameters):

       - web_search_preview: Can be used as "web_search_preview" or with optional config
         (user_location, search_context_size)
       - image_generation: Can be used as "image_generation" or with optional config (background, input_image_mask)
       - local_shell: Can be used as "local_shell" (WARNING: Only works with codex-mini-latest model)

    **Tools that REQUIRE dict configuration** (have required parameters):

       - file_search: MUST use dict with vector_store_ids (List[str])
       - computer_use_preview: MUST use dict with display_height (int), display_width (int), environment (str)
       - code_interpreter: MUST use dict with container (str)
       - mcp: MUST use dict with server_label (str), server_url (str)

       Using required-parameter tools in string format will raise a ValueError with helpful error messages.
       The tools parameter type annotation only accepts string values for tools that don't require parameters.

    Note:
        Custom tools (autogen FunctionTool or other user-defined tools) are not supported by this agent.
        Only OpenAI built-in tools provided via the Responses API are supported.


    Args:
        name (str): Name of the agent
        description (str): Description of the agent's purpose
        client (Union[AsyncOpenAI, AsyncAzureOpenAI]): OpenAI client instance
        model (str): Model to use (e.g. "gpt-4.1")
        instructions (str): System instructions for the agent
        tools (Optional[Iterable[Union[str, BuiltinToolConfig]]]): Tools the agent can use.
            Supported string values (no required parameters): "web_search_preview", "image_generation", "local_shell".
            Dict values can provide configuration for built-in tools with parameters.
            Required parameters for built-in tools:
            - file_search: vector_store_ids (List[str])
            - computer_use_preview: display_height (int), display_width (int), environment (str)
            - code_interpreter: container (str)
            - mcp: server_label (str), server_url (str)
            Optional parameters for built-in tools:
            - file_search: max_num_results (int), ranking_options (dict), filters (dict)
            - web_search_preview: user_location (str or dict), search_context_size (int)
            - image_generation: background (str), input_image_mask (str)
            - mcp: allowed_tools (List[str]), headers (dict), require_approval (bool)
            Special tools with model restrictions:
            - local_shell: Only works with "codex-mini-latest" model (WARNING: Very limited support)
            Custom tools are not supported.
        temperature (Optional[float]): Temperature for response generation (default: 1)
        max_output_tokens (Optional[int]): Maximum output tokens
        json_mode (bool): Whether to use JSON mode (default: False)
        store (bool): Whether to store conversations (default: True)
        truncation (str): Truncation strategy (default: "disabled")

    Example:

        Basic usage with built-in tools:

        .. code-block:: python

            import asyncio

            from autogen_agentchat.ui import Console
            from autogen_ext.agents.openai import OpenAIAgent
            from openai import AsyncOpenAI


            async def example():
                client = AsyncOpenAI()
                agent = OpenAIAgent(
                    name="SimpleAgent",
                    description="A simple OpenAI agent using the Responses API",
                    client=client,
                    model="gpt-4.1",
                    instructions="You are a helpful assistant.",
                    tools=["web_search_preview"],  # Only tools without required params
                )
                await Console(agent.run_stream(task="Search for recent AI developments"))


            asyncio.run(example())

        Usage with configured built-in tools:

        .. code-block:: python

            import asyncio

            from autogen_agentchat.ui import Console
            from autogen_ext.agents.openai import OpenAIAgent
            from openai import AsyncOpenAI


            async def example_with_configs():
                client = AsyncOpenAI()
                # Configure tools with required and optional parameters
                tools = [
                    # {
                    #     "type": "file_search",
                    #     "vector_store_ids": ["vs_abc123"],  # required
                    #     "max_num_results": 10,  # optional
                    # },
                    # {
                    #     "type": "computer_use_preview",
                    #     "display_height": 1024,  # required
                    #     "display_width": 1280,  # required
                    #     "environment": "linux",  # required
                    # },
                    {
                        "type": "code_interpreter",
                        "container": {"type": "auto"},  # required
                    },
                    # {
                    #     "type": "mcp",
                    #     "server_label": "my-mcp-server",  # required
                    #     "server_url": "http://localhost:3000",  # required
                    # },
                    {
                        "type": "web_search_preview",
                        "user_location": {  # optional - structured location
                            "type": "approximate",  # required: "approximate" or "exact"
                            "country": "US",  # optional
                            "region": "CA",  # optional
                            "city": "San Francisco",  # optional
                        },
                        "search_context_size": "low",  # optional
                    },
                    # "image_generation",  # Simple tools can still use string format
                ]

                agent = OpenAIAgent(
                    name="ConfiguredAgent",
                    description="An agent with configured tools",
                    client=client,
                    model="gpt-4.1",
                    instructions="You are a helpful assistant with specialized tools.",
                    tools=tools,  # type: ignore
                )
                await Console(agent.run_stream(task="Search for recent AI developments"))


            asyncio.run(example_with_configs())


        Note:
            Custom tools are not supported by OpenAIAgent. Use only built-in tools from the Responses API.

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
                    Literal["web_search_preview", "image_generation", "local_shell"],
                    BuiltinToolConfig,
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
        if tools is not None:
            for tool in tools:
                if isinstance(tool, str):
                    # Handle built-in tool types
                    self._add_builtin_tool(tool)
                elif isinstance(tool, dict) and "type" in tool:
                    # Handle configured built-in tools
                    self._tools.append(cast(dict[str, Any], tool))
                else:
                    raise ValueError(f"Unsupported tool type: {type(tool)}")

    def _add_builtin_tool(self, tool_name: str) -> None:
        """Add a built-in tool by name."""
        # Skip if an identical tool has already been registered (idempotent behaviour)
        if any(td.get("type") == tool_name for td in self._tools):
            return  # Duplicate – ignore rather than raise to stay backward-compatible
        # Only allow string format for tools that don't require parameters
        if tool_name == "web_search_preview":
            self._tools.append({"type": "web_search_preview"})
        elif tool_name == "image_generation":
            self._tools.append({"type": "image_generation"})
        elif tool_name == "local_shell":
            # Special handling for local_shell - very limited model support
            if self._model != "codex-mini-latest":
                raise ValueError(
                    f"Tool 'local_shell' is only supported with model 'codex-mini-latest', "
                    f"but current model is '{self._model}'. "
                    f"This tool is available exclusively through the Responses API and has severe limitations. "
                    f"Consider using autogen_ext.tools.code_execution.PythonCodeExecutionTool with "
                    f"autogen_ext.code_executors.local.LocalCommandLineCodeExecutor for shell execution instead."
                )
            self._tools.append({"type": "local_shell"})
        elif tool_name in ["file_search", "code_interpreter", "computer_use_preview", "mcp"]:
            # These tools require specific parameters and must use dict configuration
            raise ValueError(
                f"Tool '{tool_name}' requires specific parameters and cannot be added using string format. "
                f"Use dict configuration instead. Required parameters for {tool_name}: "
                f"{self._get_required_params_help(tool_name)}"
            )
        else:
            raise ValueError(f"Unsupported built-in tool type: {tool_name}")

    def _get_required_params_help(self, tool_name: str) -> str:
        """Get help text for required parameters of a tool."""
        help_text = {
            "file_search": "vector_store_ids (List[str])",
            "code_interpreter": "container (str | dict)",
            "computer_use_preview": "display_height (int), display_width (int), environment (str)",
            "mcp": "server_label (str), server_url (str)",
        }
        return help_text.get(tool_name, "unknown parameters")

    def _convert_message_to_dict(self, message: OpenAIMessage) -> Dict[str, Any]:
        """Convert an OpenAIMessage to a Dict[str, Any]."""
        return dict(message)

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

    # Custom tool execution is not supported by this agent.

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
            # Use a readable placeholder when the API returns no content to aid debugging
            content_str: str = str(content) if content is not None else "[no content returned]"
            self._message_history.append({"role": "assistant", "content": content_str})
            final_message = TextMessage(source=self.name, content=content_str)
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
        """Convert the OpenAI agent to a declarative config.

        Serializes built-in tools to their appropriate configuration formats for JSON serialization.

        Returns:
            OpenAIAgentConfig: The configuration that can recreate this agent.
        """
        return OpenAIAgentConfig(
            name=self.name,
            description=self.description,
            model=self._model,
            instructions=self._instructions,
            tools=list(self._tools),
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            json_mode=self._json_mode,
            store=self._store,
            truncation=self._truncation,
        )

    @classmethod
    def _from_config(cls: Type["OpenAIAgent"], config: OpenAIAgentConfig) -> "OpenAIAgent":
        """Create an OpenAI agent from a declarative config.

        Handles built-in tools (from string or dict configurations).

            Args:
                config: The configuration to load the agent from.

            Returns:
                OpenAIAgent: The reconstructed agent.
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        return cls(
            name=config.name,
            description=config.description,
            client=client,
            model=config.model,
            instructions=config.instructions,
            tools=config.tools,  # type: ignore
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            json_mode=config.json_mode,
            store=config.store,
            truncation=config.truncation,
        )

    # Add public API wrappers for configuration and tools
    def to_config(self) -> OpenAIAgentConfig:
        """Public wrapper for the private _to_config method."""
        return self._to_config()

    @classmethod
    def from_config(cls, config: OpenAIAgentConfig) -> "OpenAIAgent":
        """Public wrapper for the private _from_config classmethod."""
        return cls._from_config(config)

    @property
    def tools(self) -> list[Any]:
        """Public access to the agent's tools."""
        return self._tools

    @property
    def model(self) -> str:
        """Public access to the agent's model."""
        return self._model
