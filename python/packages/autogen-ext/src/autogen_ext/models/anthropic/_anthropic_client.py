import asyncio
import base64
import inspect
import json
import logging
import re
import warnings

# from asyncio import Task
from typing import (
    Any,
    AsyncGenerator,
    Coroutine,
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
    overload,
)

import tiktoken
from anthropic import AsyncAnthropic, AsyncStream
from anthropic.types import (
    Base64ImageSourceParam,
    ContentBlock,
    ImageBlockParam,
    Message,
    MessageParam,
    RawMessageStreamEvent,  # type: ignore
    TextBlock,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
)
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
from pydantic import BaseModel, SecretStr
from typing_extensions import Self, Unpack

from . import _model_info
from .config import AnthropicClientConfiguration, AnthropicClientConfigurationConfigModel

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

# Common parameters for message creation
anthropic_message_params = {
    "system",
    "messages",
    "max_tokens",
    "temperature",
    "top_p",
    "top_k",
    "stop_sequences",
    "tools",
    "tool_choice",
    "stream",
    "metadata",
}
disallowed_create_args = {"stream", "messages"}
required_create_args: Set[str] = {"model"}

anthropic_init_kwargs = set(inspect.getfullargspec(AsyncAnthropic.__init__).kwonlyargs)


def _anthropic_client_from_config(config: Mapping[str, Any]) -> AsyncAnthropic:
    # Filter config to only include valid parameters
    client_config = {k: v for k, v in config.items() if k in anthropic_init_kwargs}
    return AsyncAnthropic(**client_config)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in anthropic_message_params or k == "model"}
    create_args_keys = set(create_args.keys())

    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")

    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")

    return create_args


def type_to_role(message: LLMMessage) -> str:
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    else:
        return "tool"


def get_mime_type_from_image(image: Image) -> Literal["image/jpeg", "image/png", "image/gif", "image/webp"]:
    """Get a valid Anthropic media type from an Image object."""
    # Get base64 data first
    base64_data = image.to_base64()

    # Decode the base64 string
    image_data = base64.b64decode(base64_data)

    # Check the first few bytes for known signatures
    if image_data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
        return "image/gif"
    elif image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
        return "image/webp"
    else:
        # Default to JPEG as a fallback
        return "image/jpeg"


@overload
def __empty_content_to_whitespace(content: str) -> str: ...


@overload
def __empty_content_to_whitespace(content: List[Any]) -> Iterable[Any]: ...


def __empty_content_to_whitespace(
    content: Union[str, List[Union[str, Image]]],
) -> Union[str, Iterable[Any]]:
    if isinstance(content, str) and not content.strip():
        return " "
    elif isinstance(content, list) and not any(isinstance(x, str) and not x.strip() for x in content):
        for idx, message in enumerate(content):
            if isinstance(message, str) and not message.strip():
                content[idx] = " "

    return content


def user_message_to_anthropic(message: UserMessage) -> MessageParam:
    assert_valid_name(message.source)

    if isinstance(message.content, str):
        return {
            "role": "user",
            "content": __empty_content_to_whitespace(message.content),
        }
    else:
        blocks: List[Union[TextBlockParam, ImageBlockParam]] = []

        for part in message.content:
            if isinstance(part, str):
                blocks.append(TextBlockParam(type="text", text=__empty_content_to_whitespace(part)))
            elif isinstance(part, Image):
                blocks.append(
                    ImageBlockParam(
                        type="image",
                        source=Base64ImageSourceParam(
                            type="base64",
                            media_type=get_mime_type_from_image(part),
                            data=part.to_base64(),
                        ),
                    )
                )
            else:
                raise ValueError(f"Unknown content type: {part}")

        return {
            "role": "user",
            "content": blocks,
        }


def system_message_to_anthropic(message: SystemMessage) -> str:
    return __empty_content_to_whitespace(message.content)


def assistant_message_to_anthropic(message: AssistantMessage) -> MessageParam:
    assert_valid_name(message.source)

    if isinstance(message.content, list):
        # Tool calls
        tool_use_blocks: List[ToolUseBlock] = []

        for func_call in message.content:
            # Parse the arguments and convert to dict if it's a JSON string
            args = func_call.arguments
            args = __empty_content_to_whitespace(args)
            if isinstance(args, str):
                try:
                    args_dict = json.loads(args)
                except json.JSONDecodeError:
                    args_dict = {"text": args}
            else:
                args_dict = args

            tool_use_blocks.append(
                ToolUseBlock(
                    type="tool_use",
                    id=func_call.id,
                    name=func_call.name,
                    input=args_dict,
                )
            )

        # Include thought if available
        content_blocks: List[ContentBlock] = []
        if hasattr(message, "thought") and message.thought is not None:
            content_blocks.append(TextBlock(type="text", text=message.thought))

        content_blocks.extend(tool_use_blocks)

        return {
            "role": "assistant",
            "content": content_blocks,
        }
    else:
        # Simple text content
        return {
            "role": "assistant",
            "content": message.content,
        }


def tool_message_to_anthropic(message: FunctionExecutionResultMessage) -> List[MessageParam]:
    # Create a single user message containing all tool results
    content_blocks: List[ToolResultBlockParam] = []

    for result in message.content:
        content_blocks.append(
            ToolResultBlockParam(
                type="tool_result",
                tool_use_id=result.call_id,
                content=result.content,
            )
        )

    return [
        {
            "role": "user",  # Changed from "tool" to "user"
            "content": content_blocks,
        }
    ]


def to_anthropic_type(message: LLMMessage) -> Union[str, List[MessageParam], MessageParam]:
    if isinstance(message, SystemMessage):
        return system_message_to_anthropic(message)
    elif isinstance(message, UserMessage):
        return user_message_to_anthropic(message)
    elif isinstance(message, AssistantMessage):
        return assistant_message_to_anthropic(message)
    else:
        return tool_message_to_anthropic(message)


def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[ToolParam]:
    result: List[ToolParam] = []

    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool

        # Convert parameters to match Anthropic's schema format
        tool_params: Dict[str, Any] = {}
        if "parameters" in tool_schema:
            params = tool_schema["parameters"]

            # Transfer properties
            if "properties" in params:
                tool_params["properties"] = params["properties"]

            # Transfer required fields
            if "required" in params:
                tool_params["required"] = params["required"]

            # Handle schema type
            if "type" in params:
                tool_params["type"] = params["type"]
            else:
                tool_params["type"] = "object"

        result.append(
            ToolParam(
                name=tool_schema["name"],
                input_schema=tool_params,
                description=tool_schema.get("description", ""),
            )
        )

        # Check if the tool has a valid name
        assert_valid_name(tool_schema["name"])

    return result


def normalize_name(name: str) -> str:
    """

    def __init__(self, **kwargs: Unpack[AnthropicClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for AnthropicChatCompletionClient")

        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        client = _anthropic_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_info=model_info,
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _anthropic_client_from_config(state["_raw_config"])

    def _to_config(self) -> AnthropicClientConfigurationConfigModel:
        copied_config = self._raw_config.copy()
        return AnthropicClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: AnthropicClientConfigurationConfigModel) -> Self:
        copied_config = config.model_copy().model_dump(exclude_none=True)
        return cls(**copied_config)
    Normalize names by replacing invalid characters with underscore.
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]


def assert_valid_name(name: str) -> str:
    """
    Ensure that configured names are valid, raises ValueError if not.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
    if len(name) > 64:
        raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
    return name


def normalize_stop_reason(stop_reason: str | None) -> FinishReasons:
    if stop_reason is None:
        return "unknown"

    # Convert to lowercase for comparison
    stop_reason = stop_reason.lower()

    # Map Anthropic stop reasons to standard reasons
    KNOWN_STOP_MAPPINGS: Dict[str, FinishReasons] = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "function_calls",
    }

    return KNOWN_STOP_MAPPINGS.get(stop_reason, "unknown")


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    return RequestUsage(
        prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
        completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
    )


class BaseAnthropicChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        client: AsyncAnthropic,
        *,
        create_args: Dict[str, Any],
        model_info: Optional[ModelInfo] = None,
    ):
        self._client = client

        if model_info is None:
            try:
                self._model_info = _model_info.get_info(create_args["model"])
            except KeyError as err:
                raise ValueError("model_info is required when model name is not recognized") from err
        else:
            self._model_info = model_info

        # Validate model_info
        validate_model_info(self._model_info)

        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def _serialize_message(self, message: MessageParam) -> Dict[str, Any]:
        """Convert an Anthropic MessageParam to a JSON-serializable format."""
        if isinstance(message, dict):
            result: Dict[str, Any] = {}
            for key, value in message.items():
                if key == "content" and isinstance(value, list):
                    serialized_blocks: List[Any] = []
                    for block in value:  # type: ignore
                        if isinstance(block, BaseModel):
                            serialized_blocks.append(block.model_dump())
                        else:
                            serialized_blocks.append(block)
                    result[key] = serialized_blocks
                else:
                    result[key] = value
            return result
        else:
            return {"role": "unknown", "content": str(message)}

    def _merge_system_messages(self, messages: Sequence[LLMMessage]) -> Sequence[LLMMessage]:
        """
        Merge continuous system messages into a single message.
        """
        _messages: List[LLMMessage] = []
        system_message_content = ""
        _first_system_message_idx = -1
        _last_system_message_idx = -1
        # Index of the first system message for adding the merged system message at the correct position
        for idx, message in enumerate(messages):
            if isinstance(message, SystemMessage):
                if _first_system_message_idx == -1:
                    _first_system_message_idx = idx
                elif _last_system_message_idx + 1 != idx:
                    # That case, system message is not continuous
                    # Merge system messages only contiues system messages
                    raise ValueError("Multiple and Not continuous system messages are not supported")
                system_message_content += message.content + "\n"
                _last_system_message_idx = idx
            else:
                _messages.append(message)
        system_message_content = system_message_content.rstrip()
        if system_message_content != "":
            system_message = SystemMessage(content=system_message_content)
            _messages.insert(_first_system_message_idx, system_message)
        messages = _messages

        return messages

    def _rstrip_last_assistant_message(self, messages: Sequence[LLMMessage]) -> Sequence[LLMMessage]:
        """
        Remove the last assistant message if it is empty.
        """
        # When Claude models last message is AssistantMessage, It could not end with whitespace
        if isinstance(messages[-1], AssistantMessage):
            if isinstance(messages[-1].content, str):
                messages[-1].content = messages[-1].content.rstrip()

        return messages

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        # Copy create args and update with extra args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # Check for vision capability if images are present
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        # Handle JSON output format
        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            elif isinstance(json_output, type):
                raise ValueError("Structured output is currently not supported for Anthropic models")

        # Process system message separately
        system_message = None
        anthropic_messages: List[MessageParam] = []

        # Merge continuous system messages into a single message
        messages = self._merge_system_messages(messages)
        messages = self._rstrip_last_assistant_message(messages)

        for message in messages:
            if isinstance(message, SystemMessage):
                if system_message is not None:
                    # if that case, system message is must only one
                    raise ValueError("Multiple system messages are not supported")
                system_message = to_anthropic_type(message)
            else:
                anthropic_message = to_anthropic_type(message)
                if isinstance(anthropic_message, list):
                    anthropic_messages.extend(anthropic_message)
                elif isinstance(anthropic_message, str):
                    msg = MessageParam(
                        role="user" if isinstance(message, UserMessage) else "assistant", content=anthropic_message
                    )
                    anthropic_messages.append(msg)
                else:
                    anthropic_messages.append(anthropic_message)

        # Check for function calling support
        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        # Set up the request
        request_args: Dict[str, Any] = {
            "model": create_args["model"],
            "messages": anthropic_messages,
            "max_tokens": create_args.get("max_tokens", 4096),
            "temperature": create_args.get("temperature", 1.0),
        }

        # Add system message if present
        if system_message is not None:
            request_args["system"] = system_message

        has_tool_results = any(isinstance(msg, FunctionExecutionResultMessage) for msg in messages)

        # Store and add tools if present
        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            self._last_used_tools = converted_tools
            request_args["tools"] = converted_tools
        elif has_tool_results:
            # anthropic requires tools to be present even if there is any tool use
            request_args["tools"] = self._last_used_tools

        # Optional parameters
        for param in ["top_p", "top_k", "stop_sequences", "metadata"]:
            if param in create_args:
                request_args[param] = create_args[param]

        # Execute the request
        future: asyncio.Task[Message] = asyncio.ensure_future(self._client.messages.create(**request_args))  # type: ignore

        if cancellation_token is not None:
            cancellation_token.link_future(future)  # type: ignore

        result: Message = cast(Message, await future)  # type: ignore

        # Extract usage statistics
        usage = RequestUsage(
            prompt_tokens=result.usage.input_tokens,
            completion_tokens=result.usage.output_tokens,
        )
        serializable_messages: List[Dict[str, Any]] = [self._serialize_message(msg) for msg in anthropic_messages]

        logger.info(
            LLMCallEvent(
                messages=serializable_messages,
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        # Process the response
        content: Union[str, List[FunctionCall]]
        thought = None

        # Check if the response includes tool uses
        tool_uses = [block for block in result.content if getattr(block, "type", None) == "tool_use"]

        if tool_uses:
            # Handle tool use response
            content = []

            # Check for text content that should be treated as thought
            text_blocks: List[TextBlock] = [block for block in result.content if isinstance(block, TextBlock)]
            if text_blocks:
                thought = "".join([block.text for block in text_blocks])

            # Process tool use blocks
            for tool_use in tool_uses:
                if isinstance(tool_use, ToolUseBlock):
                    tool_input = tool_use.input
                    if isinstance(tool_input, dict):
                        tool_input = json.dumps(tool_input)
                    else:
                        tool_input = str(tool_input) if tool_input is not None else ""

                    content.append(
                        FunctionCall(
                            id=tool_use.id,
                            name=normalize_name(tool_use.name),
                            arguments=tool_input,
                        )
                    )
        else:
            # Handle text response
            content = "".join([block.text if isinstance(block, TextBlock) else "" for block in result.content])

        # Create the final result
        response = CreateResult(
            finish_reason=normalize_stop_reason(result.stop_reason),
            content=content,
            usage=usage,
            cached=False,
            thought=thought,
            raw_response=result,
        )

        # Update usage statistics
        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        max_consecutive_empty_chunk_tolerance: int = 0,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Creates an AsyncGenerator that yields a stream of completions based on the provided messages and tools.
        """
        # Copy create args and update with extra args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # Check for vision capability if images are present
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        # Handle JSON output format
        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}

            if isinstance(json_output, type):
                raise ValueError("Structured output is currently not supported for Anthropic models")

        # Process system message separately
        system_message = None
        anthropic_messages: List[MessageParam] = []

        # Merge continuous system messages into a single message
        messages = self._merge_system_messages(messages)
        messages = self._rstrip_last_assistant_message(messages)

        for message in messages:
            if isinstance(message, SystemMessage):
                if system_message is not None:
                    # if that case, system message is must only one
                    raise ValueError("Multiple system messages are not supported")
                system_message = to_anthropic_type(message)
            else:
                anthropic_message = to_anthropic_type(message)
                if isinstance(anthropic_message, list):
                    anthropic_messages.extend(anthropic_message)
                elif isinstance(anthropic_message, str):
                    msg = MessageParam(
                        role="user" if isinstance(message, UserMessage) else "assistant", content=anthropic_message
                    )
                    anthropic_messages.append(msg)
                else:
                    anthropic_messages.append(anthropic_message)

        # Check for function calling support
        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        # Set up the request
        request_args: Dict[str, Any] = {
            "model": create_args["model"],
            "messages": anthropic_messages,
            "max_tokens": create_args.get("max_tokens", 4096),
            "temperature": create_args.get("temperature", 1.0),
            "stream": True,
        }

        # Add system message if present
        if system_message is not None:
            request_args["system"] = system_message

        # Check if any message is a tool result
        has_tool_results = any(isinstance(msg, FunctionExecutionResultMessage) for msg in messages)

        # Add tools if present
        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            self._last_used_tools = converted_tools
            request_args["tools"] = converted_tools
        elif has_tool_results:
            request_args["tools"] = self._last_used_tools

        # Optional parameters
        for param in ["top_p", "top_k", "stop_sequences", "metadata"]:
            if param in create_args:
                request_args[param] = create_args[param]

        # Stream the response
        stream_future: asyncio.Task[AsyncStream[RawMessageStreamEvent]] = asyncio.ensure_future(
            cast(Coroutine[Any, Any, AsyncStream[RawMessageStreamEvent]], self._client.messages.create(**request_args))
        )

        if cancellation_token is not None:
            cancellation_token.link_future(stream_future)  # type: ignore

        stream: AsyncStream[RawMessageStreamEvent] = cast(AsyncStream[RawMessageStreamEvent], await stream_future)  # type: ignore

        text_content: List[str] = []
        tool_calls: Dict[str, Dict[str, Any]] = {}  # Track tool calls by ID
        current_tool_id: Optional[str] = None
        input_tokens: int = 0
        output_tokens: int = 0
        stop_reason: Optional[str] = None

        first_chunk = True
        serialized_messages: List[Dict[str, Any]] = [self._serialize_message(msg) for msg in anthropic_messages]

        # Process the stream
        async for chunk in stream:
            if first_chunk:
                first_chunk = False
                # Emit the start event.
                logger.info(
                    LLMStreamStartEvent(
                        messages=serialized_messages,
                    )
                )
            # Handle different event types
            if chunk.type == "content_block_start":
                if chunk.content_block.type == "tool_use":
                    # Start of a tool use block
                    current_tool_id = chunk.content_block.id
                    tool_calls[current_tool_id] = {
                        "id": chunk.content_block.id,
                        "name": chunk.content_block.name,
                        "input": "",  # Will be populated from deltas
                    }

            elif chunk.type == "content_block_delta":
                if hasattr(chunk.delta, "type") and chunk.delta.type == "text_delta":
                    # Handle text content
                    delta_text = chunk.delta.text
                    text_content.append(delta_text)
                    if delta_text:
                        yield delta_text

                # Handle tool input deltas - they come as InputJSONDelta
                elif hasattr(chunk.delta, "type") and chunk.delta.type == "input_json_delta":
                    if current_tool_id is not None and hasattr(chunk.delta, "partial_json"):
                        # Accumulate partial JSON for the current tool
                        tool_calls[current_tool_id]["input"] += chunk.delta.partial_json

            elif chunk.type == "content_block_stop":
                # End of a content block (could be text or tool)
                current_tool_id = None

            elif chunk.type == "message_delta":
                if hasattr(chunk.delta, "stop_reason") and chunk.delta.stop_reason:
                    stop_reason = chunk.delta.stop_reason

                # Get usage info if available
                if hasattr(chunk, "usage") and hasattr(chunk.usage, "output_tokens"):
                    output_tokens = chunk.usage.output_tokens

            elif chunk.type == "message_start":
                if hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                    if hasattr(chunk.message.usage, "input_tokens"):
                        input_tokens = chunk.message.usage.input_tokens
                    if hasattr(chunk.message.usage, "output_tokens"):
                        output_tokens = chunk.message.usage.output_tokens

        # Prepare the final response
        usage = RequestUsage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )

        # Determine content based on what was received
        content: Union[str, List[FunctionCall]]
        thought = None

        if tool_calls:
            # We received tool calls
            if text_content:
                # Text before tool calls is treated as thought
                thought = "".join(text_content)

            # Convert tool calls to FunctionCall objects
            content = []
            for _, tool_data in tool_calls.items():
                # Parse the JSON input if needed
                input_str = tool_data["input"]
                try:
                    # If it's valid JSON, parse it; otherwise use as-is
                    if input_str.strip().startswith("{") and input_str.strip().endswith("}"):
                        parsed_input = json.loads(input_str)
                        input_str = json.dumps(parsed_input)  # Re-serialize to ensure valid JSON
                except json.JSONDecodeError:
                    # Keep as string if not valid JSON
                    pass

                content.append(
                    FunctionCall(
                        id=tool_data["id"],
                        name=normalize_name(tool_data["name"]),
                        arguments=input_str,
                    )
                )
        else:
            # Just text content
            content = "".join(text_content)

        future: asyncio.Task[Message] = asyncio.ensure_future(
            self._client.messages.create(**request_args)  # type: ignore
        )

        message_result: Message = cast(Message, await future)

        # Create the final result
        result = CreateResult(
            finish_reason=normalize_stop_reason(stop_reason),
            content=content,
            usage=usage,
            cached=False,
            thought=thought,
            raw_response=message_result,
        )

        # Emit the end event.
        logger.info(
            LLMStreamEndEvent(
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        # Update usage statistics
        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        yield result

    async def close(self) -> None:
        await self._client.close()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        """
        Estimate the number of tokens used by messages and tools.

        Note: This is an estimation based on common tokenization patterns and may not perfectly
        match Anthropic's exact token counting for Claude models.
        """
        # Use cl100k_base encoding as an approximation for Claude's tokenizer
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            encoding = tiktoken.get_encoding("gpt2")  # Fallback

        num_tokens = 0

        # System message tokens (if any)
        system_content = None
        for message in messages:
            if isinstance(message, SystemMessage):
                system_content = message.content
                break

        if system_content:
            num_tokens += len(encoding.encode(system_content)) + 15  # Approximate system message overhead

        # Message tokens
        for message in messages:
            if isinstance(message, SystemMessage):
                continue  # Already counted

            # Base token cost per message
            num_tokens += 10  # Approximate message role & formatting overhead

            # Content tokens
            if isinstance(message, UserMessage) or isinstance(message, AssistantMessage):
                if isinstance(message.content, str):
                    num_tokens += len(encoding.encode(message.content))
                elif isinstance(message.content, list):
                    # Handle different content types
                    for part in message.content:
                        if isinstance(part, str):
                            num_tokens += len(encoding.encode(part))
                        elif isinstance(part, Image):
                            # Estimate vision tokens (simplified)
                            num_tokens += 512  # Rough estimation for image tokens
                        elif isinstance(part, FunctionCall):
                            num_tokens += len(encoding.encode(part.name))
                            num_tokens += len(encoding.encode(part.arguments))
                            num_tokens += 10  # Function call overhead
            elif isinstance(message, FunctionExecutionResultMessage):
                for result in message.content:
                    num_tokens += len(encoding.encode(result.content))
                    num_tokens += 10  # Function result overhead

        # Tool tokens
        for tool in tools:
            if isinstance(tool, Tool):
                tool_schema = tool.schema
            else:
                tool_schema = tool

            # Name and description
            num_tokens += len(encoding.encode(tool_schema["name"]))
            if "description" in tool_schema:
                num_tokens += len(encoding.encode(tool_schema["description"]))

            # Parameters
            if "parameters" in tool_schema:
                params = tool_schema["parameters"]

                if "properties" in params:
                    for prop_name, prop_schema in params["properties"].items():
                        num_tokens += len(encoding.encode(prop_name))

                        if "type" in prop_schema:
                            num_tokens += len(encoding.encode(prop_schema["type"]))

                        if "description" in prop_schema:
                            num_tokens += len(encoding.encode(prop_schema["description"]))

                        # Special handling for enums
                        if "enum" in prop_schema:
                            for value in prop_schema["enum"]:
                                if isinstance(value, str):
                                    num_tokens += len(encoding.encode(value))
                                else:
                                    num_tokens += 2  # Non-string enum values

            # Tool overhead
            num_tokens += 20

        return num_tokens

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        """Calculate the remaining tokens based on the model's token limit."""
        token_limit = _model_info.get_token_limit(self._create_args["model"])
        return token_limit - self.count_tokens(messages, tools=tools)

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        warnings.warn("capabilities is deprecated, use model_info instead", DeprecationWarning, stacklevel=2)
        return self._model_info

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info


class AnthropicChatCompletionClient(
    BaseAnthropicChatCompletionClient, Component[AnthropicClientConfigurationConfigModel]
):
    """
    Chat completion client for Anthropic's Claude models.

    Args:
        model (str): The Claude model to use (e.g., "claude-3-sonnet-20240229", "claude-3-opus-20240229")
        api_key (str, optional): Anthropic API key. Required if not in environment variables.
        base_url (str, optional): Override the default API endpoint.
        max_tokens (int, optional): Maximum tokens in the response. Default is 4096.
        temperature (float, optional): Controls randomness. Lower is more deterministic. Default is 1.0.
        top_p (float, optional): Controls diversity via nucleus sampling. Default is 1.0.
        top_k (int, optional): Controls diversity via top-k sampling. Default is -1 (disabled).
        model_info (ModelInfo, optional): The capabilities of the model. Required if using a custom model.

    To use this client, you must install the Anthropic extension:

    .. code-block:: bash

        pip install "autogen-ext[anthropic]"

    Example:

    .. code-block:: python

        import asyncio
        from autogen_ext.models.anthropic import AnthropicChatCompletionClient
        from autogen_core.models import UserMessage


        async def main():
            anthropic_client = AnthropicChatCompletionClient(
                model="claude-3-sonnet-20240229",
                api_key="your-api-key",  # Optional if ANTHROPIC_API_KEY is set in environment
            )

            result = await anthropic_client.create([UserMessage(content="What is the capital of France?", source="user")])  # type: ignore
            print(result)


        if __name__ == "__main__":
            asyncio.run(main())

    To load the client from a configuration:

    .. code-block:: python

        from autogen_core.models import ChatCompletionClient

        config = {
            "provider": "AnthropicChatCompletionClient",
            "config": {"model": "claude-3-sonnet-20240229"},
        }

        client = ChatCompletionClient.load_component(config)
    """

    component_type = "model"
    component_config_schema = AnthropicClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.anthropic.AnthropicChatCompletionClient"

    def __init__(self, **kwargs: Unpack[AnthropicClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for AnthropicChatCompletionClient")

        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        client = _anthropic_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_info=model_info,
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _anthropic_client_from_config(state["_raw_config"])

    def _to_config(self) -> AnthropicClientConfigurationConfigModel:
        copied_config = self._raw_config.copy()
        return AnthropicClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: AnthropicClientConfigurationConfigModel) -> Self:
        copied_config = config.model_copy().model_dump(exclude_none=True)

        # Handle api_key as SecretStr
        if "api_key" in copied_config and isinstance(config.api_key, SecretStr):
            copied_config["api_key"] = config.api_key.get_secret_value()

        return cls(**copied_config)
