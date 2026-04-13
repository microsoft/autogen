"""Cohere chat completion client implementation."""

import asyncio
import inspect
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Literal, Mapping, Optional, Sequence, Set, Union

from autogen_core import (
    EVENT_LOGGER_NAME,
    TRACE_LOGGER_NAME,
    CancellationToken,
    Component,
    FunctionCall,
    Image,
)
from autogen_core.logging import LLMCallEvent, LLMStreamEndEvent, LLMStreamStartEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
    validate_model_info,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_core.utils import extract_json_from_str
from cohere import AsyncClientV2
from cohere.types import (
    AssistantChatMessageV2,
    Content,
    ImageUrl,
    ImageUrlContent,
    NonStreamedChatResponse,
    TextContent,
    ToolCall,
    ToolCallV2,
    ToolContent,
    ToolMessageV2,
)
from cohere.types import (
    SystemChatMessageV2 as CohereSystemMessage,
)
from cohere.types import (
    UserChatMessageV2 as CohereUserMessage,
)
from pydantic import BaseModel, SecretStr
from typing_extensions import Self, Unpack

from . import _model_info
from .config import (
    CohereClientConfiguration,
    CohereClientConfigurationConfigModel,
)

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

# Common parameters for message creation
cohere_message_params = {
    "model",
    "messages",
    "max_tokens",
    "temperature",
    "p",
    "k",
    "seed",
    "stop_sequences",
    "frequency_penalty",
    "presence_penalty",
    "tool_choice",
    "tools",
    "response_format",
    "logprobs",
    "safety_mode",
    "stream",
}
disallowed_create_args = {"stream", "messages"}
required_create_args: Set[str] = {"model"}

# Get all valid parameters for AsyncClientV2 (both positional and keyword-only)
_spec = inspect.getfullargspec(AsyncClientV2.__init__)
cohere_init_kwargs = set(_spec.args[1:] if _spec.args else [])  # Skip 'self'
if _spec.kwonlyargs:
    cohere_init_kwargs.update(_spec.kwonlyargs)


def _cohere_client_from_config(config: Mapping[str, Any]) -> AsyncClientV2:
    """Create Cohere AsyncClientV2 from configuration."""
    # Filter config to only include valid parameters
    client_config = {k: v for k, v in config.items() if k in cohere_init_kwargs}

    # Convert SecretStr to string for api_key if needed
    if "api_key" in client_config and isinstance(client_config["api_key"], SecretStr):
        client_config["api_key"] = client_config["api_key"].get_secret_value()

    # Set default timeout if not provided (120 seconds for long-running requests)
    if "timeout" not in client_config:
        client_config["timeout"] = 120.0

    return AsyncClientV2(**client_config)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Extract create arguments from configuration."""
    create_args = {k: v for k, v in config.items() if k in cohere_message_params or k == "model"}
    create_args_keys = set(create_args.keys())

    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")

    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")

    return create_args


def normalize_name(name: str) -> str:
    """Normalize names by replacing invalid characters with underscore."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]


def assert_valid_name(name: str) -> str:
    """Ensure that configured names are valid, raises ValueError if not."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
    if len(name) > 64:
        raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
    return name


def normalize_stop_reason(stop_reason: str | None) -> FinishReasons:
    """Map Cohere stop reasons to standard finish reasons."""
    if stop_reason is None:
        return "unknown"

    # Convert to uppercase for Cohere's convention
    stop_reason = stop_reason.upper()

    KNOWN_STOP_MAPPINGS: Dict[str, FinishReasons] = {
        "COMPLETE": "stop",
        "MAX_TOKENS": "length",
        "STOP_SEQUENCE": "stop",
        "TOOL_CALL": "function_calls",
        "ERROR": "unknown",
        "TIMEOUT": "unknown",
    }

    return KNOWN_STOP_MAPPINGS.get(stop_reason, "unknown")


def system_message_to_cohere(message: SystemMessage) -> CohereSystemMessage:
    """Convert SystemMessage to Cohere system message format."""
    return CohereSystemMessage(content=message.content)


def user_message_to_cohere(message: UserMessage) -> CohereUserMessage:
    """Convert UserMessage to Cohere user message format."""
    assert_valid_name(message.source)

    if isinstance(message.content, str):
        return CohereUserMessage(content=message.content)
    else:
        # Multimodal content: List[str | Image]
        content_blocks: List[Content] = []

        for part in message.content:
            if isinstance(part, str):
                # Text content
                content_blocks.append(TextContent(type="text", text=part))
            elif isinstance(part, Image):
                # Image content - convert to ImageUrlContent
                # Image objects in autogen_core only have data_uri property
                content_blocks.append(
                    ImageUrlContent(
                        type="image_url",
                        image_url=ImageUrl(url=part.data_uri),
                    )
                )

        return CohereUserMessage(content=content_blocks)


def assistant_message_to_cohere(message: AssistantMessage) -> AssistantChatMessageV2:
    """Convert AssistantMessage to Cohere assistant message format."""
    assert_valid_name(message.source)

    if isinstance(message.content, list):
        # Tool calls
        tool_calls: List[ToolCallV2] = []

        for func_call in message.content:
            # Parse the arguments
            args = func_call.arguments
            if isinstance(args, str):
                try:
                    json_objs = extract_json_from_str(args)
                    if len(json_objs) == 1:
                        args_dict = json_objs[0]
                    else:
                        args_dict = {"text": args}
                except json.JSONDecodeError:
                    args_dict = {"text": args}
            else:
                args_dict = args

            tool_calls.append(
                ToolCallV2(
                    id=func_call.id,
                    function=ToolCall(
                        name=func_call.name,
                        arguments=json.dumps(args_dict) if isinstance(args_dict, dict) else str(args_dict),
                    ),
                    type="function",
                )
            )

        # Create content with tool calls
        content: List[Union[TextContent, ToolCallV2]] = []
        if hasattr(message, "thought") and message.thought is not None:
            content.append(TextContent(type="text", text=message.thought))

        content.extend(tool_calls)

        return AssistantChatMessageV2(content=content)
    else:
        # Simple text content - Cohere expects content to be a string
        return AssistantChatMessageV2(content=message.content if message.content else "")


def tool_message_to_cohere(message: FunctionExecutionResultMessage) -> List[ToolMessageV2]:
    """Convert FunctionExecutionResultMessage to Cohere tool message format."""
    tool_messages: List[ToolMessageV2] = []

    for result in message.content:
        tool_messages.append(
            ToolMessageV2(
                role="tool",
                tool_call_id=result.call_id,
                content=[
                    ToolContent(
                        type="tool_result",
                        text=result.content,
                    )
                ],
            )
        )

    return tool_messages


def to_cohere_type(
    message: LLMMessage,
) -> Union[CohereSystemMessage, CohereUserMessage, AssistantChatMessageV2, List[ToolMessageV2]]:
    """Convert LLMMessage to appropriate Cohere message type."""
    if isinstance(message, SystemMessage):
        return system_message_to_cohere(message)
    elif isinstance(message, UserMessage):
        return user_message_to_cohere(message)
    elif isinstance(message, AssistantMessage):
        return assistant_message_to_cohere(message)
    else:
        return tool_message_to_cohere(message)


def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[Dict[str, Any]]:
    """Convert AutoGen tools to Cohere tools format."""
    result: List[Dict[str, Any]] = []

    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool

        # Cohere tool format
        cohere_tool: Dict[str, Any] = {
            "type": "function",
            "function": {
                "name": tool_schema["name"],
                "description": tool_schema.get("description", ""),
            },
        }

        # Add parameters if present
        if "parameters" in tool_schema:
            cohere_tool["function"]["parameters"] = tool_schema["parameters"]

        result.append(cohere_tool)

        # Check if the tool has a valid name
        assert_valid_name(tool_schema["name"])

    return result


def convert_tool_choice_cohere(
    tool_choice: Tool | Literal["auto", "required", "none"],
) -> Optional[Literal["REQUIRED", "NONE"]]:
    """Convert tool_choice parameter to Cohere API format."""
    if tool_choice == "none":
        return "NONE"
    elif tool_choice == "required":
        return "REQUIRED"
    elif tool_choice == "auto":
        return None  # Cohere default behavior
    elif isinstance(tool_choice, Tool):
        # Cohere doesn't support forcing a specific tool, only REQUIRED or NONE
        return "REQUIRED"
    else:
        return None


class CohereChatCompletionClient(ChatCompletionClient, Component[CohereClientConfigurationConfigModel]):
    """Chat completion client for Cohere models using v2 API.

    To use this client, you must install the `cohere` extra:

    .. code-block:: bash

        pip install "autogen-ext[cohere]"

    This client allows you to interact with Cohere's chat models through the v2 API.

    Args:
        model (str): The name of the Cohere model to use (e.g., "command-r-plus-08-2024").
        api_key (optional, str): The Cohere API key. If not provided, will use the CO_API_KEY environment variable.
        base_url (optional, str): Custom base URL for the Cohere API.
        timeout (optional, float): Request timeout in seconds. Defaults to 120 seconds for long-running requests.
        max_retries (optional, int): Maximum number of retries for failed requests.
        model_info (optional, ModelInfo): Override model capabilities.
        **kwargs: Additional parameters to pass to the Cohere client.

    Examples:

        The following code snippet shows how to use the client:

        .. code-block:: python

            import asyncio
            from autogen_core.models import UserMessage
            from autogen_ext.models.cohere import CohereChatCompletionClient


            async def main():
                client = CohereChatCompletionClient(
                    model="command-r-plus-08-2024",
                    api_key="your-api-key",
                )
                result = await client.create([UserMessage(content="What is the capital of France?", source="user")])
                print(result)


            asyncio.run(main())
    """

    component_type = "model"
    component_config_schema = CohereClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.cohere.CohereChatCompletionClient"

    def __init__(self, **kwargs: Unpack[CohereClientConfiguration]) -> None:
        """Initialize the Cohere chat completion client."""
        if "model" not in kwargs:
            raise ValueError("model is required for CohereChatCompletionClient")

        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        # Extract model_info if provided
        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]
        elif "model" in kwargs:
            # Get model info from model name
            model_info = _model_info.get_model_info(kwargs["model"])

        # Validate model info
        if model_info:
            validate_model_info(model_info)

        self._model_info = model_info or ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="unknown",
            structured_output=True,
            multiple_system_messages=False,
        )

        # Create client and extract create args
        self._client = _cohere_client_from_config(copied_args)
        self._create_args = _create_args_from_config(copied_args)

        # Track token usage
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def __getstate__(self) -> Dict[str, Any]:
        """Prepare state for pickling."""
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Restore state from pickling."""
        self.__dict__.update(state)
        self._client = _cohere_client_from_config(state["_raw_config"])
        # ModelInfo is TypedDict (a dict), no conversion needed

    def _to_config(self) -> CohereClientConfigurationConfigModel:
        """Convert to configuration model."""
        copied_config = self._raw_config.copy()
        return CohereClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: CohereClientConfigurationConfigModel) -> Self:
        """Create client from configuration model."""
        copied_config = config.model_copy().model_dump(exclude_none=True)
        return cls(**copied_config)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Create a chat completion."""
        # Prepare create arguments
        create_args = dict(self._create_args)
        create_args.update(extra_create_args)

        # Convert messages to Cohere format
        converted_messages: List[Any] = []
        for msg in messages:
            cohere_msg = to_cohere_type(msg)
            if isinstance(cohere_msg, list):
                converted_messages.extend(cohere_msg)
            else:
                converted_messages.append(cohere_msg)

        # Filter out empty assistant messages (Cohere doesn't support them)
        # Keep only messages with non-empty content or tool calls
        filtered_messages: List[Any] = []
        for msg in converted_messages:
            if isinstance(msg, AssistantChatMessageV2):
                # Check if message has content
                if isinstance(msg.content, str):
                    # Skip if empty string
                    if msg.content.strip():
                        filtered_messages.append(msg)
                elif isinstance(msg.content, list):
                    # Has tool calls or other content
                    if len(msg.content) > 0:
                        filtered_messages.append(msg)
            else:
                # Keep all other message types
                filtered_messages.append(msg)

        converted_messages = filtered_messages

        # Validate message sequence (Cohere requires alternating user/assistant messages)
        # Log message roles for debugging
        message_roles = [msg.role if hasattr(msg, "role") else type(msg).__name__ for msg in converted_messages]
        logger.info(f"Message sequence before API call: {message_roles}")

        # Check for consecutive messages with same role (except system and tool)
        for i in range(len(converted_messages) - 1):
            current_msg = converted_messages[i]
            next_msg = converted_messages[i + 1]

            # Get roles
            current_role = getattr(current_msg, "role", None)
            next_role = getattr(next_msg, "role", None)

            # Skip system and tool messages in this check
            if current_role in ("system", "tool") or next_role in ("system", "tool"):
                continue

            # Check for consecutive user or assistant messages
            if current_role == next_role and current_role in ("user", "assistant"):
                logger.warning(
                    f"Found consecutive {current_role} messages at positions {i} and {i+1}. "
                    f"This may cause API errors."
                )

        # Handle tools - only if model supports function calling
        if tools and len(tools) > 0:
            # ModelInfo is TypedDict, so access it as a dict
            function_calling_supported = self._model_info.get("function_calling", True)

            if function_calling_supported:
                create_args["tools"] = convert_tools(tools)
                cohere_tool_choice = convert_tool_choice_cohere(tool_choice)
                if cohere_tool_choice:
                    create_args["tool_choice"] = cohere_tool_choice
            else:
                # Model doesn't support tools - log warning
                logger.warning(
                    f"Model {self._create_args.get('model')} does not support tool calling. "
                    f"Tools parameter will be ignored."
                )

        # Handle JSON output
        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            create_args["response_format"] = {
                "type": "json_object",
                "json_schema": json_output.model_json_schema(),
            }
        elif json_output is True:
            create_args["response_format"] = {"type": "json_object"}

        # Make API call directly (already in async context)
        # Check cancellation before making the call
        if cancellation_token and cancellation_token.is_cancelled():
            raise asyncio.CancelledError("Request was cancelled")

        try:
            response: NonStreamedChatResponse = await self._client.chat(
                messages=converted_messages,
                **create_args,
            )
        except Exception as e:
            # Log detailed error information for debugging
            error_msg = f"Cohere API error: {str(e)}"
            logger.error(f"{error_msg}\nMessage count: {len(converted_messages)}\nMessage roles: {message_roles}")

            # Check if it's an UnprocessableEntityError with "No valid response generated"
            if "No valid response generated" in str(e) or "422" in str(e):
                logger.error(
                    f"Cohere returned 'No valid response generated' error. "
                    f"This usually indicates an issue with message format or sequence. "
                    f"Message details: {message_roles}"
                )
                # Log first few messages for debugging (avoid logging sensitive content)
                for i, msg in enumerate(converted_messages[:3]):
                    msg_type = type(msg).__name__
                    msg_role = getattr(msg, "role", "N/A")
                    logger.error(f"  Message {i}: type={msg_type}, role={msg_role}")

            raise

        # Extract usage information
        usage = RequestUsage(
            prompt_tokens=int(response.usage.tokens.input_tokens) if response.usage and response.usage.tokens else 0,
            completion_tokens=int(response.usage.tokens.output_tokens)
            if response.usage and response.usage.tokens
            else 0,
        )
        self._total_usage = RequestUsage(
            prompt_tokens=self._total_usage.prompt_tokens + usage.prompt_tokens,
            completion_tokens=self._total_usage.completion_tokens + usage.completion_tokens,
        )
        self._actual_usage = usage

        # Parse response
        content: List[FunctionCall] | str = ""
        thought: str | None = None

        if response.message:
            if isinstance(response.message.content, list):
                # Check for tool calls
                tool_calls = [
                    item for item in response.message.content if hasattr(item, "type") and item.type == "tool_call"
                ]
                text_items = [
                    item for item in response.message.content if hasattr(item, "type") and item.type == "text"
                ]

                if tool_calls:
                    content = []
                    for tool_call in tool_calls:
                        # Extract function call information
                        content.append(
                            FunctionCall(
                                id=tool_call.id,
                                name=normalize_name(tool_call.function.name),
                                arguments=tool_call.function.arguments,
                            )
                        )

                    # Set thought if there's text content
                    if text_items:
                        thought = " ".join([item.text for item in text_items if hasattr(item, "text")])
                else:
                    # Text-only response
                    if text_items:
                        content = " ".join([item.text for item in text_items if hasattr(item, "text")])
            elif isinstance(response.message.content, str):
                content = response.message.content

        # Create result
        finish_reason = normalize_stop_reason(response.finish_reason if response.finish_reason else None)

        create_result = CreateResult(
            content=content,
            thought=thought,
            usage=usage,
            finish_reason=finish_reason,
            cached=False,
        )

        # Log the event
        logger.info(
            LLMCallEvent(
                messages=[
                    {
                        "role": getattr(msg, "role", "unknown"),
                        "content": str(getattr(msg, "message", getattr(msg, "content", msg))),
                    }
                    for msg in converted_messages
                ],
                response=create_result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        return create_result

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Create a streaming chat completion."""
        # ModelInfo is TypedDict - no conversion needed

        # Prepare create arguments
        create_args = dict(self._create_args)
        create_args.update(extra_create_args)
        # Note: chat_stream() doesn't need stream=True parameter

        # Convert messages to Cohere format
        converted_messages: List[Any] = []
        for msg in messages:
            cohere_msg = to_cohere_type(msg)
            if isinstance(cohere_msg, list):
                converted_messages.extend(cohere_msg)
            else:
                converted_messages.append(cohere_msg)

        # Filter out empty assistant messages (Cohere doesn't support them)
        filtered_messages: List[Any] = []
        for msg in converted_messages:
            if isinstance(msg, AssistantChatMessageV2):
                # Check if message has content
                if isinstance(msg.content, str):
                    # Skip if empty string
                    if msg.content.strip():
                        filtered_messages.append(msg)
                elif isinstance(msg.content, list):
                    # Has tool calls or other content
                    if len(msg.content) > 0:
                        filtered_messages.append(msg)
            else:
                # Keep all other message types
                filtered_messages.append(msg)

        converted_messages = filtered_messages

        # Validate message sequence (Cohere requires alternating user/assistant messages)
        message_roles = [msg.role if hasattr(msg, "role") else type(msg).__name__ for msg in converted_messages]
        logger.info(f"Stream message sequence: {message_roles}")

        # Handle tools - only if model supports function calling
        if tools and len(tools) > 0:
            # ModelInfo is TypedDict, so access it as a dict
            function_calling_supported = self._model_info.get("function_calling", True)
            if function_calling_supported:
                create_args["tools"] = convert_tools(tools)
                cohere_tool_choice = convert_tool_choice_cohere(tool_choice)
                if cohere_tool_choice:
                    create_args["tool_choice"] = cohere_tool_choice
            else:
                # Model doesn't support tools - log warning
                logger.warning(
                    f"Model {self._create_args.get('model')} does not support tool calling. "
                    f"Tools parameter will be ignored."
                )

        # Handle JSON output
        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            create_args["response_format"] = {
                "type": "json_object",
                "json_schema": json_output.model_json_schema(),
            }
        elif json_output is True:
            create_args["response_format"] = {"type": "json_object"}

        # Log stream start
        logger.info(LLMStreamStartEvent(messages=messages))

        # Make streaming API call (chat_stream is already an async generator, no await needed)
        try:
            stream = self._client.chat_stream(
                messages=converted_messages,
                **create_args,
            )
        except Exception as e:
            # Log detailed error information for debugging
            error_msg = f"Cohere stream API error: {str(e)}"
            logger.error(f"{error_msg}\nMessage count: {len(converted_messages)}\nMessage roles: {message_roles}")

            if "No valid response generated" in str(e) or "422" in str(e):
                logger.error(
                    f"Cohere returned 'No valid response generated' error in streaming mode. "
                    f"Message details: {message_roles}"
                )

            raise

        accumulated_content = ""
        usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

        try:
            async for event in stream:
                if event.type == "content-delta":
                    if hasattr(event.delta, "message") and hasattr(event.delta.message, "content"):
                        if hasattr(event.delta.message.content, "text"):
                            text = event.delta.message.content.text
                            accumulated_content += text
                            yield text
                elif event.type == "message-end":
                    # Extract usage from final event
                    if hasattr(event, "usage") and event.usage:
                        usage = RequestUsage(
                            prompt_tokens=int(event.usage.tokens.input_tokens) if event.usage.tokens else 0,
                            completion_tokens=int(event.usage.tokens.output_tokens) if event.usage.tokens else 0,
                        )
                        self._total_usage = RequestUsage(
                            prompt_tokens=self._total_usage.prompt_tokens + usage.prompt_tokens,
                            completion_tokens=self._total_usage.completion_tokens + usage.completion_tokens,
                        )
                        self._actual_usage = usage
        except Exception as stream_error:
            # Log streaming errors with message context
            logger.error(
                f"Error during stream processing: {str(stream_error)}\n"
                f"Message count: {len(converted_messages)}\n"
                f"Message roles: {message_roles}"
            )
            raise

        finally:
            # Log stream end
            logger.info(
                LLMStreamEndEvent(
                    response=accumulated_content,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )
            )

        # Yield final result
        yield CreateResult(
            content=accumulated_content,
            usage=usage,
            finish_reason="stop",
            cached=False,
        )

    @property
    def capabilities(self) -> ModelInfo:
        """Get model capabilities."""
        # ModelInfo is TypedDict (a dict), return as-is
        return self._model_info

    @property
    def model_info(self) -> ModelInfo:
        """Get model information (alias for capabilities)."""
        # ModelInfo is TypedDict (a dict), return as-is
        return self._model_info

    def count_tokens(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        **kwargs: Any,
    ) -> int:
        """Count tokens in messages (approximation)."""
        # Cohere doesn't provide a direct tokenization API in the same way
        # We'll approximate based on character count (rough estimate: 4 chars per token)
        total_chars = sum(len(str(msg.content)) for msg in messages)
        return total_chars // 4

    def remaining_tokens(
        self,
        messages: Sequence[SystemMessage | UserMessage | AssistantMessage | FunctionExecutionResultMessage],
        **kwargs: Any,
    ) -> int:
        """Calculate remaining tokens (approximation)."""
        # Assuming a context window of 128k tokens for modern Cohere models
        # This should be adjusted based on the specific model
        max_tokens = 128000
        used_tokens = self.count_tokens(messages)
        return max(max_tokens - used_tokens, 0)

    def actual_usage(self) -> RequestUsage:
        """Get actual usage from the last request."""
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        """Get total usage across all requests."""
        return self._total_usage

    async def close(self) -> None:
        """Close the client."""
        # Cohere client doesn't require explicit closing
        pass


__all__ = ["CohereChatCompletionClient"]
