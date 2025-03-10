import asyncio
import inspect
import json
import logging
import math
import re
import warnings
from asyncio import Task
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

import tiktoken
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
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from ollama import AsyncClient, ChatResponse, Message
from ollama import Image as OllamaImage
from ollama import Tool as OllamaTool
from ollama._types import ChatRequest
from pydantic import BaseModel
from typing_extensions import Self, Unpack

from . import _model_info
from .config import BaseOllamaClientConfiguration, BaseOllamaClientConfigurationConfigModel

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

# TODO: support more kwargs. Can't automate the list like we can with openai or azure because ollama uses an untyped kwargs blob for initialization.
ollama_init_kwargs = set(["host"])

# TODO: add kwarg checking logic later
# create_kwargs = set(completion_create_params.CompletionCreateParamsBase.__annotations__.keys()) | set(
#     ("timeout", "stream")
# )
# # Only single choice allowed
# disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
# required_create_args: Set[str] = set(["model"])


def _ollama_client_from_config(config: Mapping[str, Any]) -> AsyncClient:
    # Take a copy
    copied_config = dict(config).copy()
    # Shave down the config to just the AzureOpenAIChatCompletionClient kwargs
    ollama_config = {k: v for k, v in copied_config.items() if k in ollama_init_kwargs}
    return AsyncClient(**ollama_config)


ollama_chat_request_fields: dict[str, Any] = [m for m in inspect.getmembers(ChatRequest) if m[0] == "model_fields"][0][
    1
]
OLLAMA_VALID_CREATE_KWARGS_KEYS = set(ollama_chat_request_fields.keys()) | set(
    ("model", "messages", "tools", "stream", "format", "options", "keep_alive")
)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k.lower(): v for k, v in config.items() if k.lower() in OLLAMA_VALID_CREATE_KWARGS_KEYS}
    dropped_keys = [k for k in config.keys() if k.lower() not in OLLAMA_VALID_CREATE_KWARGS_KEYS]
    logger.info(f"Dropped the following unrecognized keys from create_args: {dropped_keys}")

    return create_args
    # create_args = {k: v for k, v in config.items() if k in create_kwargs}
    # create_args_keys = set(create_args.keys())
    # if not required_create_args.issubset(create_args_keys):
    #     raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")
    # if disallowed_create_args.intersection(create_args_keys):
    #     raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")
    # return create_args


# TODO check types
# oai_system_message_schema = type2schema(ChatCompletionSystemMessageParam)
# oai_user_message_schema = type2schema(ChatCompletionUserMessageParam)
# oai_assistant_message_schema = type2schema(ChatCompletionAssistantMessageParam)
# oai_tool_message_schema = type2schema(ChatCompletionToolMessageParam)


def type_to_role(message: LLMMessage) -> str:  # return type: Message.role
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    else:
        return "tool"


def user_message_to_ollama(message: UserMessage) -> Sequence[Message]:
    assert_valid_name(message.source)
    if isinstance(message.content, str):
        return [
            Message(
                content=message.content,
                role="user",
                # name=message.source, # TODO: No name parameter in Ollama
            )
        ]
    else:
        ollama_messages: List[Message] = []
        for part in message.content:
            if isinstance(part, str):
                ollama_messages.append(Message(content=part, role="user"))
            elif isinstance(part, Image):
                # TODO: should images go into their own message? Should each image get its own message?
                if not ollama_messages:
                    ollama_messages.append(Message(role="user", images=[OllamaImage(value=part.to_base64())]))
                else:
                    if ollama_messages[-1].images is None:
                        ollama_messages[-1].images = [OllamaImage(value=part.to_base64())]
                    else:
                        ollama_messages[-1].images.append(OllamaImage(value=part.to_base64()))  # type: ignore
            else:
                raise ValueError(f"Unknown content type: {part}")
        return ollama_messages


def system_message_to_ollama(message: SystemMessage) -> Message:
    return Message(
        content=message.content,
        role="system",
    )


def _func_args_to_ollama_args(args: str) -> Dict[str, Any]:
    return json.loads(args)  # type: ignore


def func_call_to_ollama(message: FunctionCall) -> Message.ToolCall:
    return Message.ToolCall(
        function=Message.ToolCall.Function(
            name=message.name,
            arguments=_func_args_to_ollama_args(message.arguments),
        )
    )


def tool_message_to_ollama(
    message: FunctionExecutionResultMessage,
) -> Sequence[Message]:
    return [Message(content=x.content, role="tool") for x in message.content]


def assistant_message_to_ollama(
    message: AssistantMessage,
) -> Message:
    assert_valid_name(message.source)
    if isinstance(message.content, list):
        return Message(
            tool_calls=[func_call_to_ollama(x) for x in message.content],
            role="assistant",
            # name=message.source,
        )
    else:
        return Message(
            content=message.content,
            role="assistant",
        )


def to_ollama_type(message: LLMMessage) -> Sequence[Message]:
    if isinstance(message, SystemMessage):
        return [system_message_to_ollama(message)]
    elif isinstance(message, UserMessage):
        return user_message_to_ollama(message)
    elif isinstance(message, AssistantMessage):
        return [assistant_message_to_ollama(message)]
    else:
        return tool_message_to_ollama(message)


# TODO: Is this correct? Do we need this?
def calculate_vision_tokens(image: Image, detail: str = "auto") -> int:
    MAX_LONG_EDGE = 2048
    BASE_TOKEN_COUNT = 85
    TOKENS_PER_TILE = 170
    MAX_SHORT_EDGE = 768
    TILE_SIZE = 512

    if detail == "low":
        return BASE_TOKEN_COUNT

    width, height = image.image.size

    # Scale down to fit within a MAX_LONG_EDGE x MAX_LONG_EDGE square if necessary

    if width > MAX_LONG_EDGE or height > MAX_LONG_EDGE:
        aspect_ratio = width / height
        if aspect_ratio > 1:
            # Width is greater than height
            width = MAX_LONG_EDGE
            height = int(MAX_LONG_EDGE / aspect_ratio)
        else:
            # Height is greater than or equal to width
            height = MAX_LONG_EDGE
            width = int(MAX_LONG_EDGE * aspect_ratio)

    # Resize such that the shortest side is MAX_SHORT_EDGE if both dimensions exceed MAX_SHORT_EDGE
    aspect_ratio = width / height
    if width > MAX_SHORT_EDGE and height > MAX_SHORT_EDGE:
        if aspect_ratio > 1:
            # Width is greater than height
            height = MAX_SHORT_EDGE
            width = int(MAX_SHORT_EDGE * aspect_ratio)
        else:
            # Height is greater than or equal to width
            width = MAX_SHORT_EDGE
            height = int(MAX_SHORT_EDGE / aspect_ratio)

    # Calculate the number of tiles based on TILE_SIZE

    tiles_width = math.ceil(width / TILE_SIZE)
    tiles_height = math.ceil(height / TILE_SIZE)
    total_tiles = tiles_width * tiles_height
    # Calculate the total tokens based on the number of tiles and the base token count

    total_tokens = BASE_TOKEN_COUNT + TOKENS_PER_TILE * total_tiles

    return total_tokens


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    return RequestUsage(
        prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
        completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
    )


# Ollama's tools follow a stricter protocol than OAI or us. While OAI accepts a map of [str, Any], Ollama requires a map of [str, Property] where Property is a typed object containing a type and description. Therefore, only the keys "type" and "description" will be converted from the properties blob in the tool schema
def convert_tools(
    tools: Sequence[Tool | ToolSchema],
) -> List[OllamaTool]:
    result: List[OllamaTool] = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool
        parameters = tool_schema["parameters"] if "parameters" in tool_schema else None
        ollama_properties: Mapping[str, OllamaTool.Function.Parameters.Property] | None = None
        if parameters is not None:
            ollama_properties = {}
            for prop_name, prop_schema in parameters["properties"].items():
                ollama_properties[prop_name] = OllamaTool.Function.Parameters.Property(
                    type=prop_schema["type"],
                    description=prop_schema["description"] if "description" in prop_schema else None,
                )
        result.append(
            OllamaTool(
                function=OllamaTool.Function(
                    name=tool_schema["name"],
                    description=tool_schema["description"] if "description" in tool_schema else "",
                    parameters=OllamaTool.Function.Parameters(
                        required=parameters["required"]
                        if parameters is not None and "required" in parameters
                        else None,
                        properties=ollama_properties,
                    ),
                ),
            )
        )
    # Check if all tools have valid names.
    for tool_param in result:
        assert_valid_name(tool_param["function"]["name"])
    return result


def normalize_name(name: str) -> str:
    """
    LLMs sometimes ask functions while ignoring their own format requirements, this function should be used to replace invalid characters with "_".

    Prefer _assert_valid_name for validating user configuration or input
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]


def assert_valid_name(name: str) -> str:
    """
    Ensure that configured names are valid, raises ValueError if not.

    For munging LLM responses use _normalize_name to ensure LLM specified names don't break the API.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
    if len(name) > 64:
        raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
    return name


# TODO: Does this need to change?
def normalize_stop_reason(stop_reason: str | None) -> FinishReasons:
    if stop_reason is None:
        return "unknown"

    # Convert to lower case
    stop_reason = stop_reason.lower()

    KNOWN_STOP_MAPPINGS: Dict[str, FinishReasons] = {
        "end_turn": "stop",
        "tool_calls": "function_calls",
    }

    return KNOWN_STOP_MAPPINGS.get(stop_reason, "unknown")


class BaseOllamaChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        client: AsyncClient,
        *,
        create_args: Dict[str, Any],
        model_capabilities: Optional[ModelCapabilities] = None,  # type: ignore
        model_info: Optional[ModelInfo] = None,
    ):
        self._client = client
        self._model_name = create_args["model"]
        if model_capabilities is None and model_info is None:
            try:
                self._model_info = _model_info.get_info(create_args["model"])
            except KeyError as err:
                raise ValueError("model_info is required when model name is not a valid OpenAI model") from err
        elif model_capabilities is not None and model_info is not None:
            raise ValueError("model_capabilities and model_info are mutually exclusive")
        elif model_capabilities is not None and model_info is None:
            warnings.warn("model_capabilities is deprecated, use model_info instead", DeprecationWarning, stacklevel=2)
            info = cast(ModelInfo, model_capabilities)
            info["family"] = ModelFamily.UNKNOWN
            self._model_info = info
        elif model_capabilities is None and model_info is not None:
            self._model_info = model_info

        self._resolved_model: Optional[str] = None
        self._model_class: Optional[str] = None
        if "model" in create_args:
            self._resolved_model = create_args["model"]
            self._model_class = _model_info.resolve_model_class(create_args["model"])

        if (
            not self._model_info["json_output"]
            and "response_format" in create_args
            and (
                isinstance(create_args["response_format"], dict)
                and create_args["response_format"]["type"] == "json_object"
            )
        ):
            raise ValueError("Model does not support JSON output.")

        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        # Ollama doesn't have IDs for tools, so we just increment a counter
        self._tool_id = 0

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return OllamaChatCompletionClient(**config)

    def get_create_args(self) -> Mapping[str, Any]:
        return self._create_args

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        # Make sure all extra_create_args are valid
        # TODO: kwarg checking logic
        # extra_create_args_keys = set(extra_create_args.keys())
        # if not create_kwargs.issuperset(extra_create_args_keys):
        #     raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        response_format_value: Optional[Mapping[str, Any]] = None

        if "response_format" in create_args:
            value = create_args["response_format"]
            # If value is a Pydantic model class, use the beta client
            if isinstance(value, type) and issubclass(value, BaseModel):
                response_format_value = value.model_json_schema()
            else:
                # response_format_value is not a Pydantic model class
                # TODO: Should this be an warning/error?
                response_format_value = None

        # Remove 'response_format' from create_args to prevent passing it twice
        create_args_no_response_format = {k: v for k, v in create_args.items() if k != "response_format"}

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output.")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        if self.model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output.")

        ollama_messages_nested = [to_ollama_type(m) for m in messages]
        ollama_messages = [item for sublist in ollama_messages_nested for item in sublist]

        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")
        future: Task[ChatResponse]
        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            future = asyncio.ensure_future(
                self._client.chat(  # type: ignore
                    # model=self._model_name,
                    messages=ollama_messages,
                    tools=converted_tools,
                    stream=False,
                    format=response_format_value,
                    **create_args_no_response_format,
                )
            )
        else:
            future = asyncio.ensure_future(
                self._client.chat(  # type: ignore
                    # model=self._model_name,
                    messages=ollama_messages,
                    stream=False,
                    format=response_format_value,
                    **create_args_no_response_format,
                )
            )
        if cancellation_token is not None:
            cancellation_token.link_future(future)
        result: ChatResponse = await future

        usage = RequestUsage(
            # TODO backup token counting
            prompt_tokens=result.prompt_eval_count if result.prompt_eval_count is not None else 0,
            completion_tokens=(result.eval_count if result.eval_count is not None else 0),
        )

        logger.info(
            LLMCallEvent(
                messages=cast(List[Dict[str, Any]], ollama_messages),
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        if self._resolved_model is not None:
            if self._resolved_model != result.model:
                warnings.warn(
                    f"Resolved model mismatch: {self._resolved_model} != {result.model}. "
                    "Model mapping in autogen_ext.models.openai may be incorrect.",
                    stacklevel=2,
                )

        # Detect whether it is a function call or not.
        # We don't rely on choice.finish_reason as it is not always accurate, depending on the API used.
        content: Union[str, List[FunctionCall]]
        if result.message.tool_calls is not None:
            # TODO: What are possible values for done_reason?
            if result.done_reason != "tool_calls":
                warnings.warn(
                    f"Finish reason mismatch: {result.done_reason} != tool_calls "
                    "when tool_calls are present. Finish reason may not be accurate. "
                    "This may be due to the API used that is not returning the correct finish reason.",
                    stacklevel=2,
                )
            # TODO: Is this still an error condition?
            if result.message.content is not None and result.message.content != "":
                warnings.warn(
                    "Both tool_calls and content are present in the message. "
                    "This is unexpected. content will be ignored, tool_calls will be used.",
                    stacklevel=2,
                )
            # NOTE: If OAI response type changes, this will need to be updated
            content = [
                FunctionCall(
                    id=str(self._tool_id),
                    arguments=json.dumps(x.function.arguments),
                    name=normalize_name(x.function.name),
                )
                for x in result.message.tool_calls
            ]
            finish_reason = "tool_calls"
            self._tool_id += 1
        else:
            finish_reason = result.done_reason or ""
            content = result.message.content or ""

        # Ollama currently doesn't provide these.
        # Currently open ticket: https://github.com/ollama/ollama/issues/2415
        # logprobs: Optional[List[ChatCompletionTokenLogprob]] = None
        # if choice.logprobs and choice.logprobs.content:
        #     logprobs = [
        #         ChatCompletionTokenLogprob(
        #             token=x.token,
        #             logprob=x.logprob,
        #             top_logprobs=[TopLogprob(logprob=y.logprob, bytes=y.bytes) for y in x.top_logprobs],
        #             bytes=x.bytes,
        #         )
        #         for x in choice.logprobs.content
        #     ]
        response = CreateResult(
            finish_reason=normalize_stop_reason(finish_reason),
            content=content,
            usage=usage,
            cached=False,
            logprobs=None,
        )

        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        max_consecutive_empty_chunk_tolerance: int = 0,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """
        Creates an AsyncGenerator that will yield a  stream of chat completions based on the provided messages and tools.

        Args:
            messages (Sequence[LLMMessage]): A sequence of messages to be processed.
            tools (Sequence[Tool | ToolSchema], optional): A sequence of tools to be used in the completion. Defaults to `[]`.
            json_output (Optional[bool], optional): If True, the output will be in JSON format. Defaults to None.
            extra_create_args (Mapping[str, Any], optional): Additional arguments for the creation process. Default to `{}`.
            cancellation_token (Optional[CancellationToken], optional): A token to cancel the operation. Defaults to None.
            max_consecutive_empty_chunk_tolerance (int): The maximum number of consecutive empty chunks to tolerate before raising a ValueError. This seems to only be needed to set when using `AzureOpenAIChatCompletionClient`. Defaults to 0.

        Yields:
            AsyncGenerator[Union[str, CreateResult], None]: A generator yielding the completion results as they are produced.

        In streaming, the default behaviour is not return token usage counts. See: [OpenAI API reference for possible args](https://platform.openai.com/docs/api-reference/chat/create).
        However `extra_create_args={"stream_options": {"include_usage": True}}` will (if supported by the accessed API)
        return a final chunk with usage set to a RequestUsage object having prompt and completion token counts,
        all preceding chunks will have usage as None. See: [stream_options](https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream_options).

        Other examples of OPENAI supported arguments that can be included in `extra_create_args`:
            - `temperature` (float): Controls the randomness of the output. Higher values (e.g., 0.8) make the output more random, while lower values (e.g., 0.2) make it more focused and deterministic.
            - `max_tokens` (int): The maximum number of tokens to generate in the completion.
            - `top_p` (float): An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.
            - `frequency_penalty` (float): A value between -2.0 and 2.0 that penalizes new tokens based on their existing frequency in the text so far, decreasing the likelihood of repeated phrases.
            - `presence_penalty` (float): A value between -2.0 and 2.0 that penalizes new tokens based on whether they appear in the text so far, encouraging the model to talk about new topics.
        """
        # Make sure all extra_create_args are valid
        # TODO: kwarg checking logic
        # extra_create_args_keys = set(extra_create_args.keys())
        # if not create_kwargs.issuperset(extra_create_args_keys):
        #     raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        response_format_value: Optional[Mapping[str, Any]] = None

        if "response_format" in create_args:
            value = create_args["response_format"]
            # If value is a Pydantic model class, use the beta client
            if isinstance(value, type) and issubclass(value, BaseModel):
                response_format_value = value.model_json_schema()
            else:
                # response_format_value is not a Pydantic model class
                response_format_value = None

        # Remove 'response_format' from create_args to prevent passing it twice
        create_args_no_response_format = {k: v for k, v in create_args.items() if k != "response_format"}

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output.")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        if self.model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output.")

        ollama_messages_nested = [to_ollama_type(m) for m in messages]
        ollama_messages = [item for sublist in ollama_messages_nested for item in sublist]

        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            stream_future = asyncio.ensure_future(
                self._client.chat(  # type: ignore
                    # model=self._model_name,
                    messages=ollama_messages,
                    tools=converted_tools,
                    stream=True,
                    format=response_format_value,
                    **create_args_no_response_format,
                )
            )
        else:
            stream_future = asyncio.ensure_future(
                self._client.chat(  # type: ignore
                    # model=self._model_name,
                    messages=ollama_messages,
                    stream=True,
                    format=response_format_value,
                    **create_args_no_response_format,
                )
            )
        if cancellation_token is not None:
            cancellation_token.link_future(stream_future)
        stream = await stream_future

        chunk = None
        stop_reason = None
        content_chunks: List[str] = []
        full_tool_calls: List[FunctionCall] = []
        completion_tokens = 0
        first_chunk = True
        while True:
            try:
                chunk_future = asyncio.ensure_future(anext(stream))
                if cancellation_token is not None:
                    cancellation_token.link_future(chunk_future)
                chunk = await chunk_future

                if first_chunk:
                    first_chunk = False
                    # Emit the start event.
                    logger.info(
                        LLMStreamStartEvent(
                            messages=cast(List[Dict[str, Any]], ollama_messages),
                        )
                    )
                # set the stop_reason for the usage chunk to the prior stop_reason
                stop_reason = chunk.done_reason if chunk.done and stop_reason is None else stop_reason
                # First try get content
                if chunk.message.content is not None:
                    content_chunks.append(chunk.message.content)
                    if len(chunk.message.content) > 0:
                        yield chunk.message.content
                    continue

                # Otherwise, get tool calls
                if chunk.message.tool_calls is not None:
                    full_tool_calls.extend(
                        [
                            FunctionCall(
                                id=str(self._tool_id),
                                arguments=json.dumps(x.function.arguments),
                                name=normalize_name(x.function.name),
                            )
                            for x in chunk.message.tool_calls
                        ]
                    )

                # TODO: logprobs currently unsupported in ollama.
                # See: https://github.com/ollama/ollama/issues/2415
                # if choice.logprobs and choice.logprobs.content:
                #     logprobs = [
                #         ChatCompletionTokenLogprob(
                #             token=x.token,
                #             logprob=x.logprob,
                #             top_logprobs=[TopLogprob(logprob=y.logprob, bytes=y.bytes) for y in x.top_logprobs],
                #             bytes=x.bytes,
                #         )
                #         for x in choice.logprobs.content
                #     ]

            except StopAsyncIteration:
                break

        if chunk and chunk.prompt_eval_count:
            prompt_tokens = chunk.prompt_eval_count
        else:
            prompt_tokens = 0

        if stop_reason == "function_call":
            raise ValueError("Function calls are not supported in this context")

        content: Union[str, List[FunctionCall]]
        if len(content_chunks) > 1:
            content = "".join(content_chunks)
            if chunk and chunk.eval_count:
                completion_tokens = chunk.eval_count
            else:
                completion_tokens = 0
        else:
            completion_tokens = 0
            # TODO: fix assumption that dict values were added in order and actually order by int index
            # for tool_call in full_tool_calls.values():
            #     # value = json.dumps(tool_call)
            #     # completion_tokens += count_token(value, model=model)
            #     completion_tokens += 0
            content = full_tool_calls

        usage = RequestUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        result = CreateResult(
            finish_reason=normalize_stop_reason(stop_reason),
            content=content,
            usage=usage,
            cached=False,
            logprobs=None,
        )

        # Emit the end event.
        logger.info(
            LLMStreamEndEvent(
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        yield result

    async def close(self) -> None:
        pass  # ollama has no close method?

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    # TODO: probably needs work
    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        model = self._create_args["model"]
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            trace_logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        tokens_per_message = 3
        num_tokens = 0

        # Message tokens.
        for message in messages:
            num_tokens += tokens_per_message
            ollama_message = to_ollama_type(message)
            for ollama_message_part in ollama_message:
                if isinstance(message.content, Image):
                    num_tokens += calculate_vision_tokens(message.content)
                elif ollama_message_part.content is not None:
                    num_tokens += len(encoding.encode(ollama_message_part.content))
        # TODO: every model family has its own message sequence.
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

        # Tool tokens.
        ollama_tools = convert_tools(tools)
        for tool in ollama_tools:
            function = tool["function"]
            tool_tokens = len(encoding.encode(function["name"]))
            if "description" in function:
                tool_tokens += len(encoding.encode(function["description"]))
            tool_tokens -= 2
            if "parameters" in function:
                parameters = function["parameters"]
                if "properties" in parameters:
                    assert isinstance(parameters["properties"], dict)
                    for propertiesKey in parameters["properties"]:  # pyright: ignore
                        assert isinstance(propertiesKey, str)
                        tool_tokens += len(encoding.encode(propertiesKey))
                        v = parameters["properties"][propertiesKey]  # pyright: ignore
                        for field in v:  # pyright: ignore
                            if field == "type":
                                tool_tokens += 2
                                tool_tokens += len(encoding.encode(v["type"]))  # pyright: ignore
                            elif field == "description":
                                tool_tokens += 2
                                tool_tokens += len(encoding.encode(v["description"]))  # pyright: ignore
                            elif field == "enum":
                                tool_tokens -= 3
                                for o in v["enum"]:  # pyright: ignore
                                    tool_tokens += 3
                                    tool_tokens += len(encoding.encode(o))  # pyright: ignore
                            else:
                                trace_logger.warning(f"Not supported field {field}")
                    tool_tokens += 11
                    if len(parameters["properties"]) == 0:  # pyright: ignore
                        tool_tokens -= 2
            num_tokens += tool_tokens
        num_tokens += 12
        return num_tokens

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        token_limit = _model_info.get_token_limit(self._create_args["model"])
        return token_limit - self.count_tokens(messages, tools=tools)

    @property
    def capabilities(self) -> ModelCapabilities:  # type: ignore
        warnings.warn("capabilities is deprecated, use model_info instead", DeprecationWarning, stacklevel=2)
        return self._model_info

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info


# TODO: see if response_format can just be a json blob instead of a BaseModel
class OllamaChatCompletionClient(BaseOllamaChatCompletionClient, Component[BaseOllamaClientConfigurationConfigModel]):
    """Chat completion client for Ollama hosted models.

    Ollama must be installed and the appropriate model pulled.

    Args:
        model (str): Which Ollama model to use.
        host (optional, str): Model host url.
        response_format (optional, pydantic.BaseModel): The format of the response. If provided, the response will be parsed into this format as json.
        options (optional, Mapping[str, Any] | Options): Additional options to pass to the Ollama client.
        model_info (optional, ModelInfo): The capabilities of the model. **Required if the model is not listed in the ollama model info.**

    Note:
        Only models with 200k+ downloads (as of Jan 21, 2025), + phi4, deepseek-r1 have pre-defined model infos. See `this file <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-ext/src/autogen_ext/models/ollama/_model_info.py>`__ for the full list. An entry for one model encompases all parameter variants of that model.

    To use this client, you must install the `ollama` extension:

    .. code-block:: bash

        pip install "autogen-ext[ollama]"

    The following code snippet shows how to use the client with an Ollama model:

    .. code-block:: python

        from autogen_ext.models.ollama import OllamaChatCompletionClient
        from autogen_core.models import UserMessage

        ollama_client = OllamaChatCompletionClient(
            model="llama3",
        )

        result = await ollama_client.create([UserMessage(content="What is the capital of France?", source="user")])  # type: ignore
        print(result)

    To load the client from a configuration, you can use the `load_component` method:

    .. code-block:: python

        from autogen_core.models import ChatCompletionClient

        config = {
            "provider": "OllamaChatCompletionClient",
            "config": {"model": "llama3"},
        }

        client = ChatCompletionClient.load_component(config)

    To output structured data, you can use the `response_format` argument:

    .. code-block:: python

        from autogen_ext.models.ollama import OllamaChatCompletionClient
        from autogen_core.models import UserMessage
        from pydantic import BaseModel


        class StructuredOutput(BaseModel):
            first_name: str
            last_name: str


        ollama_client = OllamaChatCompletionClient(
            model="llama3",
            response_format=StructuredOutput,
        )
        result = await ollama_client.create([UserMessage(content="Who was the first man on the moon?", source="user")])  # type: ignore
        print(result)

    Note:
        Tool usage in ollama is stricter than in its OpenAI counterparts. While OpenAI accepts a map of [str, Any], Ollama requires a map of [str, Property] where Property is a typed object containing ``type`` and ``description`` fields. Therefore, only the keys ``type`` and ``description`` will be converted from the properties blob in the tool schema.

    To view the full list of available configuration options, see the :py:class:`OllamaClientConfigurationConfigModel` class.

    """

    component_type = "model"
    component_config_schema = BaseOllamaClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.ollama.OllamaChatCompletionClient"

    def __init__(self, **kwargs: Unpack[BaseOllamaClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OllamaChatCompletionClient")

        model_capabilities: Optional[ModelCapabilities] = None  # type: ignore
        copied_args = dict(kwargs).copy()
        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        client = _ollama_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)
        self._raw_config: Dict[str, Any] = copied_args
        super().__init__(
            client=client, create_args=create_args, model_capabilities=model_capabilities, model_info=model_info
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _ollama_client_from_config(state["_raw_config"])

    def _to_config(self) -> BaseOllamaClientConfigurationConfigModel:
        copied_config = self._raw_config.copy()
        return BaseOllamaClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: BaseOllamaClientConfigurationConfigModel) -> Self:
        copied_config = config.model_copy().model_dump(exclude_none=True)
        return cls(**copied_config)
