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
from typing_extensions import NotRequired

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
    search_context_size: NotRequired[int]  # optional
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
    container: str  # required - Container configuration for code execution


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
        tools (Optional[Iterable[Union[str, BuiltinToolConfig, Tool]]]): Tools the agent can use.
            Supported string values: "web_search_preview", "image_generation", "local_shell" (tools without required params).
            Tools requiring parameters must use dict configuration: "file_search", "code_interpreter",
            "computer_use_preview", "mcp".
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
            Also accepts custom Tool objects for function calling.
        temperature (Optional[float]): Temperature for response generation (default: 1)
        max_output_tokens (Optional[int]): Maximum output tokens
        json_mode (bool): Whether to use JSON mode (default: False)
        store (bool): Whether to store conversations (default: True)
        truncation (str): Truncation strategy (default: "disabled")

    Example:

        Basic usage with built-in tools:

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
                    model="gpt-4o",
                    instructions="You are a helpful assistant.",
                    tools=["web_search_preview", "image_generation"],  # Only tools without required params
                )
                response = await agent.on_messages(
                    [TextMessage(source="user", content="Search for recent AI developments")], cancellation_token
                )
                print(response)

        Usage with configured built-in tools:

        .. code-block:: python

            async def example_with_configs():
                cancellation_token = CancellationToken()
                client = AsyncOpenAI()

                # Configure tools with required and optional parameters
                tools = [
                    {
                        "type": "file_search",
                        "vector_store_ids": ["vs_abc123"],  # required
                        "max_num_results": 10,  # optional
                    },
                    {
                        "type": "computer_use_preview",
                        "display_height": 1024,  # required
                        "display_width": 1280,  # required
                        "environment": "desktop",  # required
                    },
                    {
                        "type": "code_interpreter",
                        "container": "python-3.11",  # required
                    },
                    {
                        "type": "mcp",
                        "server_label": "my-mcp-server",  # required
                        "server_url": "http://localhost:3000",  # required
                    },
                    {
                        "type": "web_search_preview",
                        "user_location": {  # optional - structured location
                            "type": "approximate",  # required: "approximate" or "exact"
                            "country": "US",  # optional
                            "region": "CA",  # optional
                            "city": "San Francisco",  # optional
                        },
                        "search_context_size": 5,  # optional
                    },
                    "image_generation",  # Simple tools can still use string format
                ]

                agent = OpenAIAgent(
                    name="Configured Agent",
                    description="An agent with configured tools",
                    client=client,
                    model="gpt-4o",
                    instructions="You are a helpful assistant with specialized tools.",
                    tools=tools,
                )
                response = await agent.on_messages(
                    [TextMessage(source="user", content="Search for recent AI developments")], cancellation_token
                )
                print(response)

        Mixed usage with custom function tools:

        .. code-block:: python

            from autogen_core.tools import Tool


            # Custom calculator tool (simplified example)
            class CalculatorTool(Tool):
                # ... implementation details ...
                pass


            async def example_mixed_tools():
                cancellation_token = CancellationToken()
                client = AsyncOpenAI()
                calculator = CalculatorTool()

                agent = OpenAIAgent(
                    name="Mixed Tools Agent",
                    description="An agent with both built-in and custom tools",
                    client=client,
                    model="gpt-4o",
                    instructions="You are a helpful assistant with calculation and web search capabilities.",
                    tools=[
                        "web_search_preview",
                        calculator,
                        {"type": "mcp", "server_label": "tools", "server_url": "http://localhost:3000"},
                    ],
                )
                response = await agent.on_messages(
                    [TextMessage(source="user", content="What's 2+2 and what's the weather like?")], cancellation_token
                )
                print(response)

        asyncio.run(example())

    .. versionchanged:: v0.4.1

       Added support for built-in tool types like file_search, web_search_preview,
       code_interpreter, computer_use_preview, image_generation, and mcp.
       Added support for tool configurations with required and optional parameters.

       BREAKING CHANGE: Built-in tools are now split into two categories:

       **Tools that can use string format** (no required parameters):
       - web_search_preview: Can be used as "web_search_preview" or with optional config (user_location, search_context_size)
       - image_generation: Can be used as "image_generation" or with optional config (background, input_image_mask)
       - local_shell: Can be used as "local_shell" (WARNING: Only works with codex-mini-latest model)

       **Tools that REQUIRE dict configuration** (have required parameters):
       - file_search: MUST use dict with vector_store_ids (List[str])
       - computer_use_preview: MUST use dict with display_height (int), display_width (int), environment (str)
       - code_interpreter: MUST use dict with container (str)
       - mcp: MUST use dict with server_label (str), server_url (str)

       Using required-parameter tools in string format will raise a ValueError with helpful error messages.

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
                        "local_shell",
                    ],
                    BuiltinToolConfig,
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
                    self._add_builtin_tool(tool)
                elif isinstance(tool, dict) and "type" in tool:
                    # Handle configured built-in tools
                    self._add_configured_tool(tool)
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

    def _add_builtin_tool(self, tool_name: str) -> None:
        """Add a built-in tool by name."""
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
            "code_interpreter": "container (str)",
            "computer_use_preview": "display_height (int), display_width (int), environment (str)",
            "mcp": "server_label (str), server_url (str)",
        }
        return help_text.get(tool_name, "unknown parameters")

    def _add_configured_tool(self, tool_config: BuiltinToolConfig) -> None:
        """Add a configured built-in tool with parameters."""
        tool_type = tool_config.get("type")
        if not tool_type:
            raise ValueError("Tool configuration must include 'type' field")

        # Initialize tool definition
        tool_def: Dict[str, Any] = {}

        # Special validation for model-restricted tools
        if tool_type == "local_shell":
            if self._model != "codex-mini-latest":
                raise ValueError(
                    f"Tool 'local_shell' is only supported with model 'codex-mini-latest', "
                    f"but current model is '{self._model}'. "
                    f"This tool is available exclusively through the Responses API and has severe limitations. "
                    f"Consider using autogen_ext.tools.code_execution.PythonCodeExecutionTool with "
                    f"autogen_ext.code_executors.local.LocalCommandLineCodeExecutor for shell execution instead."
                )
            tool_def = {"type": "local_shell"}

        # For Responses API, built-in tools are defined directly without nesting
        elif tool_type == "file_search":
            # file_search requires vector_store_ids
            fs_config = cast(FileSearchToolConfig, tool_config)
            if "vector_store_ids" not in fs_config:
                raise ValueError("file_search tool requires 'vector_store_ids' parameter")

            vector_store_ids = fs_config["vector_store_ids"]
            if not isinstance(vector_store_ids, list) or not vector_store_ids:
                raise ValueError("file_search 'vector_store_ids' must be a non-empty list of strings")
            if not all(isinstance(vid, str) and vid.strip() for vid in vector_store_ids):
                raise ValueError("file_search 'vector_store_ids' must contain non-empty strings")

            tool_def = {"type": "file_search", "vector_store_ids": vector_store_ids}
            # Optional parameters
            if "max_num_results" in fs_config:
                max_results = fs_config["max_num_results"]
                if not isinstance(max_results, int) or max_results <= 0:
                    raise ValueError("file_search 'max_num_results' must be a positive integer")
                tool_def["max_num_results"] = max_results
            if "ranking_options" in fs_config:
                tool_def["ranking_options"] = fs_config["ranking_options"]
            if "filters" in fs_config:
                tool_def["filters"] = fs_config["filters"]

        elif tool_type == "web_search_preview":
            # web_search_preview can have optional parameters
            ws_config = cast(WebSearchToolConfig, tool_config)
            tool_def = {"type": "web_search_preview"}
            if "search_context_size" in ws_config:
                context_size = ws_config["search_context_size"]
                if not isinstance(context_size, int) or context_size <= 0:
                    raise ValueError("web_search_preview 'search_context_size' must be a positive integer")
                tool_def["search_context_size"] = context_size
            if "user_location" in ws_config:
                user_location = ws_config["user_location"]
                if isinstance(user_location, str):
                    if not user_location.strip():
                        raise ValueError(
                            "web_search_preview 'user_location' must be a non-empty string when using string format"
                        )
                elif isinstance(user_location, dict):
                    if "type" not in user_location:
                        raise ValueError("web_search_preview 'user_location' dictionary must include 'type' field")
                    location_type = user_location["type"]
                    if location_type not in ["approximate", "exact"]:
                        raise ValueError("web_search_preview 'user_location' type must be 'approximate' or 'exact'")
                    # Optional fields: country, region, city can be validated if present
                    for optional_field in ["country", "region", "city"]:
                        if optional_field in user_location:
                            if (
                                not isinstance(user_location[optional_field], str)
                                or not user_location[optional_field].strip()
                            ):
                                raise ValueError(
                                    f"web_search_preview 'user_location' {optional_field} must be a non-empty string"
                                )
                else:
                    raise ValueError("web_search_preview 'user_location' must be a string or dictionary")
                tool_def["user_location"] = user_location

        elif tool_type == "computer_use_preview":
            # computer_use_preview requires display dimensions and environment
            cu_config = cast(ComputerUseToolConfig, tool_config)
            required_params = ["display_height", "display_width", "environment"]
            for param in required_params:
                if param not in cu_config:
                    raise ValueError(f"computer_use_preview tool requires '{param}' parameter")

            # Validate display dimensions
            height = cu_config["display_height"]
            width = cu_config["display_width"]
            if not isinstance(height, int) or height <= 0:
                raise ValueError("computer_use_preview 'display_height' must be a positive integer")
            if not isinstance(width, int) or width <= 0:
                raise ValueError("computer_use_preview 'display_width' must be a positive integer")

            # Validate environment
            environment = cu_config["environment"]
            if not isinstance(environment, str) or not environment.strip():
                raise ValueError("computer_use_preview 'environment' must be a non-empty string")

            tool_def = {
                "type": "computer_use_preview",
                "display_height": height,
                "display_width": width,
                "environment": environment,
            }

        elif tool_type == "mcp":
            # MCP requires server_label and server_url
            mcp_config = cast(MCPToolConfig, tool_config)
            required_params = ["server_label", "server_url"]
            for param in required_params:
                if param not in mcp_config:
                    raise ValueError(f"mcp tool requires '{param}' parameter")

            # Validate required parameters
            server_label = mcp_config["server_label"]
            server_url = mcp_config["server_url"]
            if not isinstance(server_label, str) or not server_label.strip():
                raise ValueError("mcp 'server_label' must be a non-empty string")
            if not isinstance(server_url, str) or not server_url.strip():
                raise ValueError("mcp 'server_url' must be a non-empty string")

            tool_def = {"type": "mcp", "server_label": server_label, "server_url": server_url}
            # Optional parameters
            if "allowed_tools" in mcp_config:
                allowed_tools = mcp_config["allowed_tools"]
                if not isinstance(allowed_tools, list):
                    raise ValueError("mcp 'allowed_tools' must be a list of strings")
                if not all(isinstance(tool, str) for tool in allowed_tools):
                    raise ValueError("mcp 'allowed_tools' must contain only strings")
                tool_def["allowed_tools"] = allowed_tools
            if "headers" in mcp_config:
                headers = mcp_config["headers"]
                if not isinstance(headers, dict):
                    raise ValueError("mcp 'headers' must be a dictionary")
                tool_def["headers"] = headers
            if "require_approval" in mcp_config:
                require_approval = mcp_config["require_approval"]
                if not isinstance(require_approval, bool):
                    raise ValueError("mcp 'require_approval' must be a boolean")
                tool_def["require_approval"] = require_approval

        elif tool_type == "code_interpreter":
            # code_interpreter requires container
            ci_config = cast(CodeInterpreterToolConfig, tool_config)
            if "container" not in ci_config:
                raise ValueError("code_interpreter tool requires 'container' parameter")

            container = ci_config["container"]
            if not isinstance(container, str) or not container.strip():
                raise ValueError("code_interpreter 'container' must be a non-empty string")

            tool_def = {"type": "code_interpreter", "container": container}

        elif tool_type == "image_generation":
            # image_generation can have optional parameters
            ig_config = cast(ImageGenerationToolConfig, tool_config)
            tool_def = {"type": "image_generation"}
            if "background" in ig_config:
                background = ig_config["background"]
                if not isinstance(background, str) or not background.strip():
                    raise ValueError("image_generation 'background' must be a non-empty string")
                tool_def["background"] = background
            if "input_image_mask" in ig_config:
                input_image_mask = ig_config["input_image_mask"]
                if not isinstance(input_image_mask, str) or not input_image_mask.strip():
                    raise ValueError("image_generation 'input_image_mask' must be a non-empty string")
                tool_def["input_image_mask"] = input_image_mask

        else:
            raise ValueError(f"Unsupported built-in tool type: {tool_type}")

        self._tools.append(tool_def)

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
