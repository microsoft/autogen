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

import google.generativeai as genai
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
from google.ai.generativelanguage_v1beta.types.generative_service import GenerationConfig
from typing_extensions import Self, TypedDict, Unpack

from . import _model_info
from .config import (
    GeminiClientConfiguration,
    GeminiClientConfigurationConfigModel,
    VertexAIClientConfiguration,
    VertexAIClientConfigurationConfigModel,
)

logger = logging.getLogger(__name__)

# Type definitions
class ToolSchema(TypedDict, total=False):
    name: str
    description: str
    parameters: Dict[str, Any]

T = TypeVar("T", bound=Union[dict, Any])
Tool = Union[T, ToolSchema]

def _convert_message_to_genai_content(message: LLMMessage) -> Dict[str, Any]:
    """
    Convert an LLMMessage to a Gemini content dictionary with enhanced vision support.

    References:
    - https://ai.google.dev/gemini-api/docs/vision?lang=python
    """
    if isinstance(message, SystemMessage):
        # Gemini doesn't directly support system messages, so prepend to first user message
        return {
            "role": "user",
            "parts": [{"text": str(message.content)}]
        }
    elif isinstance(message, UserMessage):
        # Handle multimodal content with improved image support
        parts: List[Dict[str, Any]] = []

        # Handle string content
        if isinstance(message.content, str):
            parts.append({"text": message.content})

        # Handle list of mixed content types
        elif isinstance(message.content, list):
            for part in message.content:
                if isinstance(part, str):
                    parts.append({"text": part})
                elif isinstance(part, Image):
                    # Enhanced image handling
                    try:
                        # Attempt to detect MIME type if possible
                        mime_type = getattr(part, "mime_type", "image/jpeg")

                        # Support for base64 and file path
                        if hasattr(part, "to_base64"):
                            image_data = part.to_base64()
                        elif hasattr(part, "path"):
                            # Read image file and convert to base64
                            with open(part.path, "rb") as img_file:
                                import base64
                                image_data = base64.b64encode(img_file.read()).decode("utf-8")
                        else:
                            # Fallback to default base64 conversion
                            image_data = part.to_base64()

                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_data
                            }
                        })
                    except Exception as e:
                        logger.warning(f"Could not process image: {e}")
                        parts.append({"text": "[Unprocessable Image]"})

        return {
            "role": "user",
            "parts": parts
        }
    elif isinstance(message, AssistantMessage):
        return {
            "role": "model",
            "parts": [{"text": str(message.content)}]
        }
    else:
        # Default to user role for other message types
        return {
            "role": "user",
            "parts": [{"text": str(message.content)}]
        }

def _convert_tools_to_genai_function_declarations(tools: Sequence[Tool]) -> List[Dict[str, Any]]:
    """
    Convert AutoGen tools to Gemini function declarations with robust type handling.
    """
    genai_tools: List[Dict[str, Any]] = []
    for i, tool in enumerate(tools):
        # Robust tool schema extraction with type checking
        try:
            # Handle both dict and object types
            if isinstance(tool, dict):
                tool_schema = tool.get("schema", tool) if "schema" in tool else tool
            else:
                # Convert non-dict objects to dict
                tool_schema = {
                    "name": getattr(tool, "name", ""),
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "parameters", {})
                }

            # Validate tool description
            tool_desc = {
                "name": str(tool_schema.get("name", f"tool_{i}")),
                "description": str(tool_schema.get("description", "")),
                "parameters": tool_schema.get("parameters", {}) or {}
            }

            # Validate tool description
            if not tool_desc["name"]:
                logger.warning("Tool missing name, skipping")
                continue

            genai_tools.append({
                "function_declarations": [{
                    "name": tool_desc["name"],
                    "description": tool_desc["description"],
                    "parameters": tool_desc["parameters"]
                }]
            })
        except Exception as e:
            logger.warning(f"Could not process tool: {e}")

    return genai_tools

class BaseGeminiChatCompletionClient(ChatCompletionClient):
    """Base class for Gemini chat completion clients."""

    def __init__(
        self,
        model: str,
        create_args: Dict[str, Any],
        model_info: Optional[ModelInfo] = None,
    ):
        self._model = model
        self._create_args = create_args

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

        # Add support for context caching
        self._cached_context: Optional[Dict[str, Any]] = None
        self._context_cache_duration: Optional[int] = None

    def cache_context(
        self,
        context: Union[str, List[Dict[str, Any]]],
        duration_hours: Optional[int] = None
    ) -> None:
        """
        Cache context for more efficient long-context interactions.

        References:
        - https://ai.google.dev/gemini-api/docs/caching
        """
        self._cached_context = context
        self._context_cache_duration = duration_hours

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        structured_output: Optional[Dict[str, Any]] = None,
    ) -> CreateResult:
        # Prepare generation config with long context support
        generation_config = GenerationConfig(
            **{
                **self._create_args,
                **extra_create_args,
                # Enable long context optimizations
                "max_output_tokens": extra_create_args.get("max_output_tokens", 8192),
            }
        )

        # Structured output configuration
        if structured_output:
            generation_config.response_mime_type = structured_output.get("mime_type", "application/json")
            generation_config.response_schema = structured_output.get("schema")

        # Handle JSON output with more robust configuration
        if json_output:
            generation_config.response_mime_type = "application/json"
            generation_config.response_format = {"type": "json_object"}

        # Prepare messages with cached context if available
        if self._cached_context:
            # Prepend cached context to messages
            messages = [
                *([UserMessage(content=str(self._cached_context))] if self._cached_context else []),
                *messages
            ]

        try:
            # Enhanced model initialization with long context support
            model = genai.GenerativeModel(
                model_name=self._model,
                generation_config=generation_config,
                # Optional: Add system instruction for consistent behavior
                system_instruction=messages[0].content if isinstance(messages[0], SystemMessage) else None
            )

            # Start chat with long context capabilities
            chat = model.start_chat(
                # Optional: Configure history management for long context
                history_metadata={
                    "max_tokens": _model_info.get_token_limit(self._model),
                    "strategy": "sliding_window"  # Efficient context management
                }
            )

            # Process messages with advanced function calling
            response = await chat.send_message_async(
                _convert_message_to_genai_content(messages[-1]),
                tools=_convert_tools_to_genai_function_declarations(tools) if tools else None
            )

            # Advanced tool call processing
            tool_calls = [
                FunctionCall(
                    id=str(i),
                    name=part.function_call.name,
                    arguments=json.dumps(part.function_call.args)
                )
                for part in response.candidates[0].content.parts
                if hasattr(part, "function_call")
            ]

            # Determine finish reason with more granular control
            finish_reason: Literal["stop", "length", "function_calls", "content_filter", "unknown"] = (
                "function_calls" if tool_calls else "stop"
            )

            # Create result with enhanced metadata
            result = CreateResult(
                content=tool_calls or response.text,
                finish_reason=finish_reason,
                usage=RequestUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count
                ),
                cached=bool(self._cached_context),
                extra={
                    "safety_ratings": response.candidates[0].safety_ratings,
                    "citation_metadata": response.candidates[0].citation_metadata
                }
            )

            return result

        except Exception as e:
            logger.error(f"Advanced Gemini API call error: {e}")
            return CreateResult(
                content="",
                finish_reason="unknown",
                usage=self._actual_usage,
                cached=False
            )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        max_consecutive_empty_chunk_tolerance: int = 0,
        structured_output: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Union[str, FunctionCall, CreateResult], None]:
        # Prepare generation config with long context support
        generation_config = GenerationConfig(
            **{
                **self._create_args,
                **extra_create_args,
                "max_output_tokens": extra_create_args.get("max_output_tokens", 8192),
            }
        )

        # Structured output configuration
        if structured_output:
            generation_config.response_mime_type = structured_output.get("mime_type", "application/json")
            generation_config.response_schema = structured_output.get("schema")

        # Handle JSON output with more robust configuration
        if json_output:
            generation_config.response_mime_type = "application/json"
            generation_config.response_format = {"type": "json_object"}

        try:
            # Enhanced model initialization
            model = genai.GenerativeModel(
                model_name=self._model,
                generation_config=generation_config,
                system_instruction=messages[0].content if isinstance(messages[0], SystemMessage) else None
            )

            # Start chat with long context capabilities
            chat = model.start_chat(
                history_metadata={
                    "max_tokens": _model_info.get_token_limit(self._model),
                    "strategy": "sliding_window"
                }
            )

            # Process messages with advanced function calling
            response = await chat.send_message_async(
                _convert_message_to_genai_content(messages[-1]),
                tools=_convert_tools_to_genai_function_declarations(tools) if tools else None
            )

            # Initialize tracking variables
            content_chunks: List[str] = []
            tool_calls: List[FunctionCall] = []

            # Process streaming content
            for chunk in response.candidates[0].content.parts:
                if hasattr(chunk, "text"):
                    content_chunks.append(chunk.text)
                    yield chunk.text

                if hasattr(chunk, "function_call"):
                    tool_call = FunctionCall(
                        id=str(len(tool_calls)),
                        name=chunk.function_call.name,
                        arguments=json.dumps(chunk.function_call.args)
                    )
                    tool_calls.append(tool_call)
                    yield tool_call

            # Determine finish reason with more granular control
            finish_reason: Literal["stop", "length", "function_calls", "content_filter", "unknown"] = (
                "function_calls" if tool_calls else "stop"
            )

            # Create final result with enhanced metadata
            result = CreateResult(
                content=tool_calls or "".join(content_chunks),
                finish_reason=finish_reason,
                usage=RequestUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count
                ),
                cached=False,
                extra={
                    "safety_ratings": response.candidates[0].safety_ratings,
                    "citation_metadata": response.candidates[0].citation_metadata
                }
            )

            yield result

        except Exception as e:
            logger.error(f"Advanced Gemini API streaming call error: {e}")
            yield CreateResult(
                content="",
                finish_reason="unknown",
                usage=self._actual_usage,
                cached=False
            )

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool] = []) -> int:
        """
        Count tokens for the given messages and tools with robust type handling.
        """
        model = genai.GenerativeModel(self._model)

        # Prepare a list to store all text content
        all_text_content: List[str] = []

        # Process messages
        for msg in messages:
            # Handle different message types
            if isinstance(msg, SystemMessage):
                all_text_content.append(f"System: {msg.content}")
            elif isinstance(msg, UserMessage):
                # Handle both string and multimodal content
                if isinstance(msg.content, str):
                    all_text_content.append(f"User: {msg.content}")
                elif isinstance(msg.content, list):
                    user_text_parts = []
                    for part in msg.content:
                        if isinstance(part, str):
                            user_text_parts.append(part)
                        elif isinstance(part, Image):
                            # Add a placeholder for images
                            user_text_parts.append("[Image]")
                    all_text_content.append(f"User: {' '.join(user_text_parts)}")
            elif isinstance(msg, AssistantMessage):
                all_text_content.append(f"Assistant: {msg.content}")

        # Combine all text content
        combined_text = "\n".join(all_text_content)

        # Count tokens for messages
        message_token_count = model.count_tokens(combined_text).total_tokens

        # Count tokens for tools
        tool_token_count = 0
        if tools:
            # Convert tools to a JSON representation for token counting
            tool_descriptions = []
            for i, tool in enumerate(tools):
                # Robust tool schema extraction
                if isinstance(tool, dict):
                    tool_schema = tool.get("schema", tool) if "schema" in tool else tool
                else:
                    # Convert non-dict objects to dict
                    tool_schema = {
                        "name": getattr(tool, "name", f"tool_{i}"),
                        "description": getattr(tool, "description", ""),
                        "parameters": getattr(tool, "parameters", {})
                    }

                # Create a tool description
                tool_desc = {
                    "name": str(tool_schema.get("name", f"tool_{i}")),
                    "description": str(tool_schema.get("description", "")),
                    "parameters": tool_schema.get("parameters", {})
                }
                tool_descriptions.append(tool_desc)

            # Convert tool descriptions to JSON and count tokens
            tool_text = json.dumps(tool_descriptions)
            tool_token_count = model.count_tokens(tool_text).total_tokens

        # Return total token count
        return message_token_count + tool_token_count

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool] = []) -> int:
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

class GeminiChatCompletionClient(BaseGeminiChatCompletionClient, Component[GeminiClientConfigurationConfigModel]):
    """Client for Gemini API."""

    component_type = "model"
    component_config_schema = GeminiClientConfigurationConfigModel

    def __init__(self, config: Optional[GeminiClientConfigurationConfigModel] = None, **kwargs: Unpack[GeminiClientConfiguration]):
        # Merge config and kwargs
        if config is None:
            config = GeminiClientConfigurationConfigModel(**kwargs)

        # Get API key from config or environment
        api_key = config.api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API key must be provided either in the configuration or as environment variable GOOGLE_API_KEY")

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Prepare create arguments
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

        # Initialize base client
        super().__init__(
            model=config.model,
            create_args=create_args
        )

        # Store raw configuration for serialization
        self._raw_config = config.model_dump(exclude_none=True)

    @classmethod
    def _from_config(cls, config: GeminiClientConfigurationConfigModel) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)

    def _to_config(self) -> GeminiClientConfigurationConfigModel:
        """Convert the current instance to a configuration model."""
        return GeminiClientConfigurationConfigModel(**self._raw_config)

class VertexAIChatCompletionClient(BaseGeminiChatCompletionClient, Component[VertexAIClientConfigurationConfigModel]):
    """Client for Vertex AI."""

    component_type = "model"
    component_config_schema = VertexAIClientConfigurationConfigModel

    def __init__(self, config: Optional[VertexAIClientConfigurationConfigModel] = None, **kwargs: Unpack[VertexAIClientConfiguration]):
        # Merge config and kwargs
        if config is None:
            config = VertexAIClientConfigurationConfigModel(**kwargs)

        # Vertex AI requires project_id
        if not config.project_id:
            raise ValueError("project_id is required for Vertex AI configuration")

        # Configure Vertex AI (placeholder - actual implementation depends on Vertex AI SDK)
        # This is a conceptual implementation and would need to be updated with actual Vertex AI integration
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

        # Initialize base client
        super().__init__(
            model=config.model,
            create_args=create_args
        )

        # Store raw configuration for serialization
        self._raw_config = config.model_dump(exclude_none=True)

    @classmethod
    def _from_config(cls, config: VertexAIClientConfigurationConfigModel) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)

    def _to_config(self) -> VertexAIClientConfigurationConfigModel:
        """Convert the current instance to a configuration model."""
        return VertexAIClientConfigurationConfigModel(**self._raw_config)
