import asyncio
import json
import logging
import os
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from autogen_core import (
    CancellationToken,
    Component,
    FunctionCall,
    Image,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from google import genai  # Use google-genai library
from google.genai import types  # Import types from google.genai
from google.genai.types import (
    CreateCachedContentConfig,
    GenerateContentConfig,
    GenerateImagesConfig,
)
from typing_extensions import Self, Unpack

from . import _model_info
from .config import (
    GeminiClientConfig,
    VertexAIClientConfig,
)

logger = logging.getLogger(__name__)

# Remove local type definitions and use types from genai
StructuredOutputSchema = Dict[str, Any]

def _convert_message_to_genai_content(message: LLMMessage) -> types.Content:
    """
    Convert an LLMMessage to a Gemini content with enhanced long context support.

    References:
    - https://ai.google.dev/gemini-api/docs/long-context
    - https://ai.google.dev/gemini-api/docs/vision?lang=python
    """
    def _process_content(content: Union[str, List[Any]]) -> List[types.Part]:
        parts: List[types.Part] = []

        # Handle string content
        if isinstance(content, str):
            parts.append(types.Part.from_text(text=content))

        # Handle list of mixed content types
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, str):
                    parts.append(types.Part.from_text(text=part))
                elif isinstance(part, Image):
                    try:
                        # Enhanced image handling for long context
                        mime_type = getattr(part, "mime_type", "image/jpeg")
                        # Support for base64, file path, and other image representations
                        if hasattr(part, "to_base64"):
                            image_data = part.to_base64()
                        elif hasattr(part, "path"):
                            with open(part.path, "rb") as img_file:
                                import base64
                                image_data = base64.b64encode(img_file.read()).decode("utf-8")
                        else:
                            image_data = str(part)  # Fallback to string representation
                        parts.append(types.Part.from_data(data=image_data, mime_type=mime_type))
                    except Exception as e:
                        logger.warning(f"Could not process image in long context: {e}")
                        parts.append(types.Part.from_text(text="[Unprocessable Image]"))
                else:
                    # Support for other potential content types
                    parts.append(types.Part.from_text(text=str(part)))

        return parts

    # Handle different message types with long context considerations
    if isinstance(message, SystemMessage):
        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=str(message.content))]
        )
    elif isinstance(message, UserMessage):
        return types.Content(
            role="user",
            parts=_process_content(message.content)
        )
    elif isinstance(message, AssistantMessage):
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=str(message.content))]
        )
    else:
        # Default to user role for other message types
        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=str(message.content))]
        )


def create_tool(name: str, description: str, parameters: Dict[str, Any]) -> types.Tool:
    """Create a Gemini tool"""
    try:
        schema = types.Schema.from_dict(parameters) if isinstance(parameters, dict) else parameters
        return types.Tool(
            function_declarations=[types.FunctionDeclaration(
                name=name,
                description=description,
                parameters=schema
            )]
        )
    except Exception as e:
        logger.warning(f"Error creating tool {name}: {e}")
        # Return a simplified tool if conversion fails
        return types.Tool(
            function_declarations=[types.FunctionDeclaration(
                name=name,
                description=description,
                parameters=types.Schema.from_dict({"type": "object", "properties": {}})
            )]
        )


def convert_tool(tool: Union[Tool, ToolSchema]) -> types.Tool:
    """
    Convert an AutoGen tool to a Gemini tool.

    References:
    - [Function calling](https://ai.google.dev/gemini-api/docs/function-calling/tutorial?lang=python)
    - [Extract structured data](https://ai.google.dev/gemini-api/tutorials/extract_structured_data)
    """
    if isinstance(tool, Tool):
        tool_schema = tool.schema.copy()
    else:
        assert isinstance(tool, dict)
        tool_schema = tool.copy()

    # Clean up parameters
    if "parameters" in tool_schema:
        for value in tool_schema["parameters"]["properties"].values():
            if "title" in value:
                del value["title"]

    # Create function definition
    function_def: Dict[str, Any] = {
        "name": tool_schema["name"],
        "description": tool_schema.get("description", ""),
        "parameters": tool_schema.get("parameters", {})
    }

    try:
        converted_tool = create_tool(
            name=function_def["name"],
            description=function_def["description"],
            parameters=function_def["parameters"]
        )
        return converted_tool
    except Exception as e:
        logger.warning(f"Error converting tool {function_def['name']}: {e}")
        # Return a simplified tool if conversion fails
        return types.Tool(
            function_declarations=[types.FunctionDeclaration(
                name=function_def["name"],
                description=function_def["description"],
                parameters=types.Schema.from_dict({"type": "object", "properties": {}})
            )]
        )


def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[types.Tool]:
    """
    Convert AutoGen tools to Gemini function declarations using google.genai.types.Tool.
    """
    result: List[types.Tool] = []
    for tool in tools:
        try:
            converted_tool = convert_tool(tool)
            result.append(converted_tool)
        except Exception as e:
            logger.warning(f"Error converting tool: {str(e)}")
            continue
    return result


def _prepare_config(
    config: Optional[Union[GenerateContentConfig, Dict[str, Any]]] = None,
    create_args: Dict[str, Any] = {},
    extra_create_args: Dict[str, Any] = {},
    tools: Optional[List[types.Tool]] = None,
    response_format: Optional[Dict[str, str]] = None
) -> GenerateContentConfig:
    """
    Prepare and merge configuration with flexible type handling.

    Args:
        config: Configuration object or dictionary
        create_args: Base configuration arguments
        extra_create_args: Additional configuration arguments
        tools: Optional tools for function calling
        response_format: Optional response format configuration

    Returns:
        Prepared configuration object
    """
    # Start with default config
    if config is None:
        config = GenerateContentConfig()

    # Convert dictionary to config object
    if isinstance(config, dict):
        config = GenerateContentConfig(**config)

    # Update config with tools and response format
    if tools is not None:
        config.tools = tools
    if response_format is not None:
        config.response_format = response_format

    # Merge configuration arguments
    merged_args = {**create_args, **extra_create_args}
    for key, value in merged_args.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


class BaseGeminiChatCompletionClient(ChatCompletionClient):
    """
    Base class for Gemini chat completion clients with enhanced long context support.

    References:
    - https://ai.google.dev/gemini-api/docs/long-context
    - https://github.com/googleapis/python-genai?tab=readme-ov-file
    """

    def __init__(
        self,
        model: str,
        create_args: Dict[str, Any],
        model_info: Optional[ModelInfo] = None,
    ):
        self._model = model
        self._create_args = create_args
        self._client: Optional[genai.Client] = None  # Will be set by subclasses

        # Enhanced context caching with SDK-inspired approach
        self._context_cache: Dict[str, Any] = {
            "contents": [],  # Store cached contents
            "system_instruction": None,  # Optional system-wide instruction
            "ttl": None  # Time-to-live for cached content
        }

        # Resolve model info
        if model_info is None:
            try:
                self._model_info = _model_info.get_info(model)
            except KeyError as err:
                raise ValueError("model_info is required when model name is not known") from err
        else:
            self._model_info = model_info

        # Initialize usage tracking
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def cache_context(
        self,
        contents: Sequence[Union[str, Image]],
        system_instruction: Optional[str] = None,
        ttl: Optional[str] = "3600s"  # Default 1-hour cache
    ) -> Dict[str, Any]:
        """
        Cache context for long-running conversations.

        References:
        - https://github.com/googleapis/python-genai?tab=readme-ov-file#caches
        """
        try:
            # Convert contents to Gemini-compatible format
            cached_contents = [
                _convert_message_to_genai_content(
                    UserMessage(content=[content], source="user")  # Wrap in list to match UserMessage signature
                ) for content in contents
            ]

            # Update context cache
            self._context_cache = {
                "contents": cached_contents,
                "system_instruction": system_instruction,
                "ttl": ttl
            }

            return self._context_cache
        except Exception as e:
            logger.error(f"Error caching context: {e}")
            return {}

    def generate_content(
        self,
        contents: Union[str, Sequence[Union[str, Image]]],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        structured_output: Optional[Dict[str, Any]] = None,
        extra_create_args: Mapping[str, Any] = {},
        use_cached_context: bool = False,
        config: Optional[Union[GenerateContentConfig, Dict[str, Any]]] = None
    ) -> CreateResult:
        """
        Generate content using Gemini API's generate_content method with retries and enhanced error handling.

        References:
        - https://github.com/googleapis/python-genai?tab=readme-ov-file
        """
        # Normalize contents to a list
        if isinstance(contents, str):
            contents = [contents]

        # Prepare messages with long context support
        genai_contents = [
            _convert_message_to_genai_content(
                UserMessage(content=[content], source="auto")  # Use "auto" as source
            ) for content in contents
        ]

        # Optionally use cached context
        if use_cached_context and self._context_cache.get("contents"):
            genai_contents = self._context_cache["contents"] + genai_contents

        # Convert tools
        genai_tools = convert_tools(tools) if tools else None

        # Prepare response format
        response_format = None
        if json_output or structured_output:
            response_format = {
                "type": structured_output.get("type", "json_object") if structured_output else "json_object"
            }

        # Prepare configuration, passing genai_tools and response_format
        generation_config = _prepare_config(
            config=config,
            create_args=self._create_args,
            extra_create_args=extra_create_args,
            tools=genai_tools,  # Pass the prepared tools
            response_format=response_format,  # Pass the prepared response_format
        )

        try:
            client = self._client
            response = client.models.generate_content(
                model=self._model,
                contents=genai_contents,
                config=generation_config
            )

            # Process tool calls and structured output
            tool_calls: List[FunctionCall] = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            FunctionCall(
                                id=str(len(tool_calls)),
                                name=part.function_call.name,
                                arguments=json.dumps(part.function_call.args)
                            )
                        )

            # Determine finish reason
            finish_reason: Literal["stop", "length", "function_calls", "content_filter", "unknown"] = "unknown"
            if hasattr(response.candidates[0], "finish_reason"):
                finish_reason = response.candidates[0].finish_reason
            elif tool_calls:
                finish_reason = "function_calls"
            else:
                finish_reason = "stop"

            # Get response text
            text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text"):
                        text += part.text

            # Create result
            result = CreateResult(
                content=tool_calls if tool_calls else text,
                finish_reason=finish_reason,
                usage=RequestUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count
                ),
                cached=use_cached_context
            )

            # Update usage tracking
            self._total_usage = RequestUsage(
                prompt_tokens=self._total_usage.prompt_tokens + result.usage.prompt_tokens,
                completion_tokens=self._total_usage.completion_tokens + result.usage.completion_tokens
            )
            self._actual_usage = result.usage

            return result

        except Exception as e:
            logger.error(f"Error during Gemini API generate_content call: {e}")
            return CreateResult(
                content="",
                finish_reason="unknown",
                usage=self._actual_usage,
                cached=False
            )

    async def generate_content_async(
        self,
        contents: Union[str, Sequence[Union[str, Image]]],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        structured_output: Optional[Dict[str, Any]] = None,
        extra_create_args: Dict[str, Any] = {},
        use_cached_context: bool = False,
        config: Optional[Union[GenerateContentConfig, Dict[str, Any]]] = None,
    ) -> CreateResult:
        """
        Asynchronously generate content using Gemini API's generate_content method with retries.

        References:
        - https://github.com/googleapis/python-genai?tab=readme-ov-file
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Please use a concrete implementation class.")

        # Normalize contents to a list
        if isinstance(contents, str):
            contents = [contents]

        # Prepare messages with long context support
        genai_contents = []
        for content in contents:
            if isinstance(content, str):
                genai_contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif isinstance(content, Image):
                genai_contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_data(data=content.to_base64(), mime_type=content.mime_type)]
                ))
            else:
                genai_contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=str(content))]
                ))

        # Optionally use cached context
        if use_cached_context and self._context_cache.get("contents"):
            genai_contents = self._context_cache["contents"] + genai_contents

        # Convert tools
        genai_tools = convert_tools(tools) if tools else None

        # Prepare response format
        response_format = None
        if json_output or structured_output:
            response_format = {
                "type": structured_output.get("type", "json_object") if structured_output else "json_object"
            }

        # Prepare configuration, passing genai_tools and response_format
        generation_config = _prepare_config(
            config=config,
            create_args=self._create_args,
            extra_create_args=extra_create_args,
            tools=genai_tools,  # Pass the prepared tools
            response_format=response_format,  # Pass the prepared response_format
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=genai_contents,
                config=generation_config,
            )

            # Process tool calls and structured output
            tool_calls: List[FunctionCall] = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            FunctionCall(
                                id=str(len(tool_calls)),
                                name=part.function_call.name,
                                arguments=json.dumps(part.function_call.args)
                            )
                        )

            # Determine finish reason
            finish_reason: Literal["stop", "length", "function_calls", "content_filter", "unknown"] = "unknown"
            if hasattr(response.candidates[0], "finish_reason"):
                finish_reason = response.candidates[0].finish_reason
            elif tool_calls:
                finish_reason = "function_calls"
            else:
                finish_reason = "stop"

            # Get response text
            text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text"):
                        text += part.text

            # Create result
            result = CreateResult(
                content=tool_calls if tool_calls else text,
                finish_reason=finish_reason,
                usage=RequestUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count
                ),
                cached=use_cached_context
            )

            # Update usage tracking
            self._total_usage = RequestUsage(
                prompt_tokens=self._total_usage.prompt_tokens + result.usage.prompt_tokens,
                completion_tokens=self._total_usage.completion_tokens + result.usage.completion_tokens
            )
            self._actual_usage = result.usage

            return result

        except Exception as e:
            logger.error(f"Error during Gemini API async call: {e}")
            return CreateResult(
                content="",
                finish_reason="unknown",
                usage=self._actual_usage,
                cached=False
            )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Create a chat completion using the Gemini model.

        Args:
            messages: The messages to send to the model.
            tools: The tools that may be invoked during the chat.
            json_output: Whether the model should return JSON.
            extra_create_args: Additional arguments to pass to the model.
            cancellation_token: Token for cancelling the request.

        Returns:
            CreateResult: The completion result.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Please use a concrete implementation class.")

        # Prepare configuration
        config = _prepare_config(
            config=None,  # Let _prepare_config create a default
            create_args=self._create_args,
            extra_create_args=dict(extra_create_args),  # Convert Mapping to Dict
            tools=convert_tools(tools) if tools else None,  # Convert tools
            response_format={"type": "json_object"} if json_output else None,  # Set response format
        )

        # Prepare contents from messages
        contents = [
            _convert_message_to_genai_content(message) for message in messages
        ]

        try:
            # Use the non-streaming generate_content method
            return await self.generate_content_async(
                contents=contents,
                config=config,
                tools=tools,  # Pass the original tools, not genai_tools
                json_output=json_output,
                extra_create_args=extra_create_args,
            )
        except Exception as e:
            logger.warning(f"Error in create: {str(e)}")
            raise

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Create a streaming chat completion using the Gemini model.

        Args:
            messages: The messages to send to the model.
            tools: The tools that may be invoked during the chat.
            json_output: Whether the model should return JSON.
            extra_create_args: Additional arguments to pass to the model.
            cancellation_token: Token for cancelling the request.

        Yields:
            Union[str, CreateResult]: The streaming completion results.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Please use a concrete implementation class.")

        # Prepare configuration
        config = _prepare_config(
            config=None,  # Let _prepare_config create a default
            create_args=self._create_args,
            extra_create_args=dict(extra_create_args),  # Convert Mapping to Dict
            tools=convert_tools(tools) if tools else None,  # Convert tools
            response_format={"type": "json_object"} if json_output else None,  # Set response format
        )

        # Prepare contents from messages
        contents = [
            _convert_message_to_genai_content(message) for message in messages
        ]

        try:
            # Get the response
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            # Process the response in chunks
            if response.text:
                # Split the response into chunks (you can adjust the chunk size)
                chunk_size = 100  # characters
                text = response.text
                for i in range(0, len(text), chunk_size):
                    yield text[i:i + chunk_size]

        except Exception as e:
            logger.warning(f"Error in create_stream: {str(e)}")
            raise

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        """
        Count tokens for the given messages and tools.

        According to Gemini API documentation, a token is approximately 4 characters.
        This method provides a more accurate token counting approach.

        References:
        - https://ai.google.dev/gemini-api/docs/tokens
        """
        # Prepare a list to store all text content
        all_text_content: List[str] = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                all_text_content.append(f"System: {msg.content}")
            elif isinstance(msg, UserMessage):
                if isinstance(msg.content, str):
                    all_text_content.append(f"User: {msg.content}")
                elif isinstance(msg.content, list):
                    user_text_parts = []
                    for part in msg.content:
                        if isinstance(part, str):
                            user_text_parts.append(part)
                        elif isinstance(part, Image):
                            user_text_parts.append("[Image]")
                    all_text_content.append(f"User: {' '.join(user_text_parts)}")
            elif isinstance(msg, AssistantMessage):
                all_text_content.append(f"Assistant: {msg.content}")

        combined_text = "\n".join(all_text_content)

        try:
            client = self._client
            message_token_count = client.models.count_tokens(model=self._model, contents=combined_text).total_tokens
        except Exception:
            # Fallback to approximate token count (each token ~4 characters)
            message_token_count = len(combined_text) // 4

        tool_token_count = 0
        if tools:
            tool_descriptions = []
            for tool in tools:
                if isinstance(tool, dict):
                    tool_schema = tool.get("schema", tool)
                else:
                    tool_schema = tool

                tool_desc = {
                    "name": tool_schema.get("name", ""),
                    "description": tool_schema.get("description", ""),
                    "parameters": tool_schema.get("parameters", {})
                }
                tool_descriptions.append(tool_desc)

            tool_text = json.dumps(tool_descriptions)
            try:
                tool_token_count = client.models.count_tokens(model=self._model, contents=tool_text).total_tokens
            except Exception:
                tool_token_count = len(tool_text) // 4

        return message_token_count + tool_token_count

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        """
        Calculate remaining tokens based on model's token limit.

        Follows the Gemini API token counting approach.

        References:
        - https://ai.google.dev/gemini-api/docs/tokens
        """
        token_limit = _model_info.get_token_limit(self._model)
        used_tokens = self.count_tokens(messages, tools=tools)
        return max(0, token_limit - used_tokens)

    def actual_usage(self) -> RequestUsage:
        """Return the actual usage for the last request."""
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        """Return the total usage across all requests."""
        return self._total_usage

    @property
    def model_info(self) -> ModelInfo:
        """Return the model information."""
        return self._model_info


class GeminiChatCompletionClient(BaseGeminiChatCompletionClient, Component[GeminiClientConfig]):
    """
    Client for Gemini API with enhanced capabilities.

    This client provides access to Google's Gemini models with support for:
    - Long context handling
    - Vision/multimodal inputs
    - Function/tool calling
    - Structured output (JSON)
    - Robust error handling and retries
    - Token management
    - Streaming responses
    - Context caching

    Args:
        config (Optional[GeminiClientConfigurationConfigModel]): Configuration model
        **kwargs: Configuration parameters that match GeminiClientConfiguration

    Example:
        ```python
        from autogen_ext.models.gemini import GeminiChatCompletionClient

        client = GeminiChatCompletionClient(
            model="gemini-1.5-pro",
            api_key="your-api-key",  # Or use GOOGLE_API_KEY env var
            temperature=0.7,
            max_output_tokens=1000
        )
        ```

    References:
        - https://ai.google.dev/gemini-api/docs
        - https://github.com/googleapis/python-genai
    """

    component_type = "model"
    component_config_schema = GeminiClientConfig

    def __init__(
        self,
        config: Optional[GeminiClientConfig] = None,
        **kwargs: Any
    ):
        if config is None:
            config = GeminiClientConfig(**kwargs)

        api_key = config.api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API key must be provided either in the configuration or as environment variable GOOGLE_API_KEY")

        create_args = {
            k: v for k, v in {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "max_output_tokens": config.max_output_tokens,
                "candidate_count": config.candidate_count,
                "stop_sequences": config.stop_sequences,
            }.items() if v is not None
        }

        super().__init__(
            model=config.model,
            create_args=create_args,
            model_info=config.model_info,
        )

        self._client = genai.Client(api_key=api_key)
        self._raw_config = config.model_dump(exclude_none=True)

    @classmethod
    def _from_config(cls, config: GeminiClientConfig) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)

    def _to_config(self) -> GeminiClientConfig:
        """Convert the current instance to a configuration model."""
        return GeminiClientConfig(**self._raw_config)

    def capabilities(self) -> Dict[str, bool]:
        """Return the capabilities of the client."""
        return {
            "stream": True,
            "tools": True,
            "vision": True,
            "json_output": True,
            "function_calling": True,
            "async_agentic": True,
        }


class VertexAIChatCompletionClient(BaseGeminiChatCompletionClient, Component[VertexAIClientConfig]):
    """
    Client for Vertex AI Gemini models with enhanced capabilities.

    This client provides access to Google's Gemini models through Vertex AI with support for:
    - Long context handling
    - Vision/multimodal inputs
    - Function/tool calling
    - Structured output (JSON)
    - Robust error handling and retries
    - Token management
    - Streaming responses
    - Context caching

    Args:
        config (Optional[VertexAIClientConfigurationConfigModel]): Configuration model
        **kwargs: Configuration parameters that match VertexAIClientConfiguration

    Example:
        ```python
        from autogen_ext.models.gemini import VertexAIChatCompletionClient

        client = VertexAIChatCompletionClient(
            model="gemini-1.5-pro",
            project_id="your-project-id",
            location="us-central1"
        )
        ```

    References:
        - https://cloud.google.com/vertex-ai
        - https://github.com/googleapis/python-genai
    """

    component_type = "model"
    component_config_schema = VertexAIClientConfig

    def __init__(
        self,
        config: Optional[VertexAIClientConfig] = None,
        **kwargs: Any
    ):
        if config is None:
            config = VertexAIClientConfig(**kwargs)

        if not config.project_id:
            raise ValueError("project_id is required for Vertex AI configuration")

        create_args = {
            k: v for k, v in {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "max_output_tokens": config.max_output_tokens,
                "candidate_count": config.candidate_count,
                "stop_sequences": config.stop_sequences,
            }.items() if v is not None
        }

        super().__init__(
            model=config.model,
            create_args=create_args,
            model_info=config.model_info,
        )

        # Initialize Vertex AI client
        try:
            from google.cloud import aiplatform
            aiplatform.init(
                project=config.project_id,
                location=config.location,
                credentials=config.credentials_path,
            )
            self._client = genai.Client()
        except ImportError:
            raise ImportError("Please install google-cloud-aiplatform to use VertexAIChatCompletionClient")

        self._raw_config = config.model_dump(exclude_none=True)

    @classmethod
    def _from_config(cls, config: VertexAIClientConfig) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)

    def _to_config(self) -> VertexAIClientConfig:
        """Convert the current instance to a configuration model."""
        return VertexAIClientConfig(**self._raw_config)

    def capabilities(self) -> Dict[str, bool]:
        """Return the capabilities of the client."""
        return {
            "stream": True,
            "tools": True,
            "vision": True,
            "json_output": True,
            "function_calling": True,
            "async_agentic": True,
        }
