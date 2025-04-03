import asyncio
import inspect
import json
import logging
import math
import os
import re
import warnings
from asyncio import Task
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
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
    ChatCompletionTokenLogprob,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
    validate_model_info,
)
from autogen_core.tools import Tool, ToolSchema
from openai import NOT_GIVEN, AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionChunk,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionRole,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
    ParsedChatCompletion,
    ParsedChoice,
    completion_create_params,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.shared_params import (
    FunctionDefinition,
    FunctionParameters,
    ResponseFormatJSONObject,
    ResponseFormatText,
)
from pydantic import BaseModel, SecretStr
from typing_extensions import Self, Unpack

from .._utils.normalize_stop_reason import normalize_stop_reason
from .._utils.parse_r1_content import parse_r1_content
from . import _model_info
from .config import (
    AzureOpenAIClientConfiguration,
    AzureOpenAIClientConfigurationConfigModel,
    OpenAIClientConfiguration,
    OpenAIClientConfigurationConfigModel,
)

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

openai_init_kwargs = set(inspect.getfullargspec(AsyncOpenAI.__init__).kwonlyargs)
aopenai_init_kwargs = set(inspect.getfullargspec(AsyncAzureOpenAI.__init__).kwonlyargs)

create_kwargs = set(completion_create_params.CompletionCreateParamsBase.__annotations__.keys()) | set(
    ("timeout", "stream")
)
# Only single choice allowed
disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
required_create_args: Set[str] = set(["model"])


def _azure_openai_client_from_config(config: Mapping[str, Any]) -> AsyncAzureOpenAI:
    # Take a copy
    copied_config = dict(config).copy()
    # Shave down the config to just the AzureOpenAIChatCompletionClient kwargs
    azure_config = {k: v for k, v in copied_config.items() if k in aopenai_init_kwargs}
    return AsyncAzureOpenAI(**azure_config)


def _openai_client_from_config(config: Mapping[str, Any]) -> AsyncOpenAI:
    # Shave down the config to just the OpenAI kwargs
    openai_config = {k: v for k, v in config.items() if k in openai_init_kwargs}
    return AsyncOpenAI(**openai_config)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in create_kwargs}
    create_args_keys = set(create_args.keys())
    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")
    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")
    return create_args


# TODO check types
# oai_system_message_schema = type2schema(ChatCompletionSystemMessageParam)
# oai_user_message_schema = type2schema(ChatCompletionUserMessageParam)
# oai_assistant_message_schema = type2schema(ChatCompletionAssistantMessageParam)
# oai_tool_message_schema = type2schema(ChatCompletionToolMessageParam)


def type_to_role(message: LLMMessage) -> ChatCompletionRole:
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    else:
        return "tool"


def user_message_to_oai(message: UserMessage, prepend_name: bool = False) -> ChatCompletionUserMessageParam:
    assert_valid_name(message.source)
    if isinstance(message.content, str):
        return ChatCompletionUserMessageParam(
            content=(f"{message.source} said:\n" if prepend_name else "") + message.content,
            role="user",
            name=message.source,
        )
    else:
        parts: List[ChatCompletionContentPartParam] = []
        for part in message.content:
            if isinstance(part, str):
                if prepend_name:
                    # Append the name to the first text part
                    oai_part = ChatCompletionContentPartTextParam(
                        text=f"{message.source} said:\n" + part,
                        type="text",
                    )
                    prepend_name = False
                else:
                    oai_part = ChatCompletionContentPartTextParam(
                        text=part,
                        type="text",
                    )
                parts.append(oai_part)
            elif isinstance(part, Image):
                # TODO: support url based images
                # TODO: support specifying details
                parts.append(cast(ChatCompletionContentPartImageParam, part.to_openai_format()))
            else:
                raise ValueError(f"Unknown content type: {part}")
        return ChatCompletionUserMessageParam(
            content=parts,
            role="user",
            name=message.source,
        )


def system_message_to_oai(message: SystemMessage) -> ChatCompletionSystemMessageParam:
    return ChatCompletionSystemMessageParam(
        content=message.content,
        role="system",
    )


def func_call_to_oai(message: FunctionCall) -> ChatCompletionMessageToolCallParam:
    return ChatCompletionMessageToolCallParam(
        id=message.id,
        function={
            "arguments": message.arguments,
            "name": message.name,
        },
        type="function",
    )


def tool_message_to_oai(
    message: FunctionExecutionResultMessage,
) -> Sequence[ChatCompletionToolMessageParam]:
    return [
        ChatCompletionToolMessageParam(content=x.content, role="tool", tool_call_id=x.call_id) for x in message.content
    ]


def assistant_message_to_oai(
    message: AssistantMessage,
) -> ChatCompletionAssistantMessageParam:
    assert_valid_name(message.source)
    if isinstance(message.content, list):
        if message.thought is not None:
            return ChatCompletionAssistantMessageParam(
                content=message.thought,
                tool_calls=[func_call_to_oai(x) for x in message.content],
                role="assistant",
                name=message.source,
            )
        else:
            return ChatCompletionAssistantMessageParam(
                tool_calls=[func_call_to_oai(x) for x in message.content],
                role="assistant",
                name=message.source,
            )
    else:
        return ChatCompletionAssistantMessageParam(
            content=message.content,
            role="assistant",
            name=message.source,
        )


def to_oai_type(message: LLMMessage, prepend_name: bool = False) -> Sequence[ChatCompletionMessageParam]:
    if isinstance(message, SystemMessage):
        return [system_message_to_oai(message)]
    elif isinstance(message, UserMessage):
        return [user_message_to_oai(message, prepend_name)]
    elif isinstance(message, AssistantMessage):
        return [assistant_message_to_oai(message)]
    else:
        return tool_message_to_oai(message)


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


def convert_tools(
    tools: Sequence[Tool | ToolSchema],
) -> List[ChatCompletionToolParam]:
    result: List[ChatCompletionToolParam] = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool

        result.append(
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool_schema["name"],
                    description=(tool_schema["description"] if "description" in tool_schema else ""),
                    parameters=(
                        cast(FunctionParameters, tool_schema["parameters"]) if "parameters" in tool_schema else {}
                    ),
                    strict=(tool_schema["strict"] if "strict" in tool_schema else False),
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


@dataclass
class CreateParams:
    messages: List[ChatCompletionMessageParam]
    tools: List[ChatCompletionToolParam]
    response_format: Optional[Type[BaseModel]]
    create_args: Dict[str, Any]


class BaseOpenAIChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        *,
        create_args: Dict[str, Any],
        model_capabilities: Optional[ModelCapabilities] = None,  # type: ignore
        model_info: Optional[ModelInfo] = None,
        add_name_prefixes: bool = False,
    ):
        self._client = client
        self._add_name_prefixes = add_name_prefixes
        if model_capabilities is None and model_info is None:
            try:
                self._model_info = _model_info.get_info(create_args["model"])
            except KeyError as err:
                raise ValueError("model_info is required when model name is not a valid OpenAI model") from err
        elif model_capabilities is not None and model_info is not None:
            raise ValueError("model_capabilities and model_info are mutually exclusive")
        elif model_capabilities is not None and model_info is None:
            warnings.warn(
                "model_capabilities is deprecated, use model_info instead",
                DeprecationWarning,
                stacklevel=2,
            )
            info = cast(ModelInfo, model_capabilities)
            info["family"] = ModelFamily.UNKNOWN
            self._model_info = info
        elif model_capabilities is None and model_info is not None:
            self._model_info = model_info

        # Validate model_info, check if all required fields are present
        validate_model_info(self._model_info)

        self._resolved_model: Optional[str] = None
        if "model" in create_args:
            self._resolved_model = _model_info.resolve_model(create_args["model"])

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

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(**config)

    def _process_create_args(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema],
        json_output: Optional[bool | type[BaseModel]],
        extra_create_args: Mapping[str, Any],
    ) -> CreateParams:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # The response format value to use for the beta client.
        response_format_value: Optional[Type[BaseModel]] = None

        if "response_format" in create_args:
            # Legacy support for getting beta client mode from response_format.
            value = create_args["response_format"]
            if isinstance(value, type) and issubclass(value, BaseModel):
                if self.model_info["structured_output"] is False:
                    raise ValueError("Model does not support structured output.")
                warnings.warn(
                    "Using response_format to specify the BaseModel for structured output type will be deprecated. "
                    "Use json_output in create and create_stream instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                response_format_value = value
                # Remove response_format from create_args to prevent passing it twice.
                del create_args["response_format"]
            # In all other cases when response_format is set to something else, we will
            # use the regular client.

        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output.")
            if json_output is True:
                # JSON mode.
                create_args["response_format"] = ResponseFormatJSONObject(type="json_object")
            elif json_output is False:
                # Text mode.
                create_args["response_format"] = ResponseFormatText(type="text")
            elif isinstance(json_output, type) and issubclass(json_output, BaseModel):
                if self.model_info["structured_output"] is False:
                    raise ValueError("Model does not support structured output.")
                if response_format_value is not None:
                    raise ValueError(
                        "response_format and json_output cannot be set to a Pydantic model class at the same time."
                    )
                # Beta client mode with Pydantic model class.
                response_format_value = json_output
            else:
                raise ValueError(f"json_output must be a boolean or a Pydantic model class, got {type(json_output)}")

        if response_format_value is not None and "response_format" in create_args:
            warnings.warn(
                "response_format is found in extra_create_args while json_output is set to a Pydantic model class. "
                "Skipping the response_format in extra_create_args in favor of the json_output. "
                "Structured output will be used.",
                UserWarning,
                stacklevel=2,
            )
            # If using beta client, remove response_format from create_args to prevent passing it twice
            del create_args["response_format"]

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if self.model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output.")

        oai_messages_nested = [to_oai_type(m, prepend_name=self._add_name_prefixes) for m in messages]
        oai_messages = [item for sublist in oai_messages_nested for item in sublist]

        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        converted_tools = convert_tools(tools)

        return CreateParams(
            messages=oai_messages,
            tools=converted_tools,
            response_format=response_format_value,
            create_args=create_args,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        create_params = self._process_create_args(
            messages,
            tools,
            json_output,
            extra_create_args,
        )
        future: Union[Task[ParsedChatCompletion[BaseModel]], Task[ChatCompletion]]
        if create_params.response_format is not None:
            # Use beta client if response_format is not None
            future = asyncio.ensure_future(
                self._client.beta.chat.completions.parse(
                    messages=create_params.messages,
                    tools=(create_params.tools if len(create_params.tools) > 0 else NOT_GIVEN),
                    response_format=create_params.response_format,
                    **create_params.create_args,
                )
            )
        else:
            # Use the regular client
            future = asyncio.ensure_future(
                self._client.chat.completions.create(
                    messages=create_params.messages,
                    stream=False,
                    tools=(create_params.tools if len(create_params.tools) > 0 else NOT_GIVEN),
                    **create_params.create_args,
                )
            )

        if cancellation_token is not None:
            cancellation_token.link_future(future)
        result: Union[ParsedChatCompletion[BaseModel], ChatCompletion] = await future
        if create_params.response_format is not None:
            result = cast(ParsedChatCompletion[Any], result)

        usage = RequestUsage(
            # TODO backup token counting
            prompt_tokens=result.usage.prompt_tokens if result.usage is not None else 0,
            completion_tokens=(result.usage.completion_tokens if result.usage is not None else 0),
        )

        logger.info(
            LLMCallEvent(
                messages=cast(List[Dict[str, Any]], create_params.messages),
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        if self._resolved_model is not None:
            if self._resolved_model != result.model:
                warnings.warn(
                    f"Resolved model mismatch: {self._resolved_model} != {result.model}. "
                    "Model mapping in autogen_ext.models.openai may be incorrect. "
                    f"Set the model to {result.model} to enhance token/cost estimation and suppress this warning.",
                    stacklevel=2,
                )

        # Limited to a single choice currently.
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], Choice] = result.choices[0]

        # Detect whether it is a function call or not.
        # We don't rely on choice.finish_reason as it is not always accurate, depending on the API used.
        content: Union[str, List[FunctionCall]]
        thought: str | None = None
        if choice.message.function_call is not None:
            raise ValueError("function_call is deprecated and is not supported by this model client.")
        elif choice.message.tool_calls is not None and len(choice.message.tool_calls) > 0:
            if choice.finish_reason != "tool_calls":
                warnings.warn(
                    f"Finish reason mismatch: {choice.finish_reason} != tool_calls "
                    "when tool_calls are present. Finish reason may not be accurate. "
                    "This may be due to the API used that is not returning the correct finish reason.",
                    stacklevel=2,
                )
            if choice.message.content is not None and choice.message.content != "":
                # Put the content in the thought field.
                thought = choice.message.content
            # NOTE: If OAI response type changes, this will need to be updated
            content = []
            for tool_call in choice.message.tool_calls:
                if not isinstance(tool_call.function.arguments, str):
                    warnings.warn(
                        f"Tool call function arguments field is not a string: {tool_call.function.arguments}."
                        "This is unexpected and may due to the API used not returning the correct type. "
                        "Attempting to convert it to string.",
                        stacklevel=2,
                    )
                    if isinstance(tool_call.function.arguments, dict):
                        tool_call.function.arguments = json.dumps(tool_call.function.arguments)
                content.append(
                    FunctionCall(
                        id=tool_call.id,
                        arguments=tool_call.function.arguments,
                        name=normalize_name(tool_call.function.name),
                    )
                )
            finish_reason = "tool_calls"
        else:
            # if not tool_calls, then it is a text response and we populate the content and thought fields.
            finish_reason = choice.finish_reason
            content = choice.message.content or ""
            # if there is a reasoning_content field, then we populate the thought field. This is for models such as R1 - direct from deepseek api.
            if choice.message.model_extra is not None:
                reasoning_content = choice.message.model_extra.get("reasoning_content")
                if reasoning_content is not None:
                    thought = reasoning_content

        logprobs: Optional[List[ChatCompletionTokenLogprob]] = None
        if choice.logprobs and choice.logprobs.content:
            logprobs = [
                ChatCompletionTokenLogprob(
                    token=x.token,
                    logprob=x.logprob,
                    top_logprobs=[TopLogprob(logprob=y.logprob, bytes=y.bytes) for y in x.top_logprobs],
                    bytes=x.bytes,
                )
                for x in choice.logprobs.content
            ]

        #   This is for local R1 models.
        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1 and thought is None:
            thought, content = parse_r1_content(content)

        response = CreateResult(
            finish_reason=normalize_stop_reason(finish_reason),
            content=content,
            usage=usage,
            cached=False,
            logprobs=logprobs,
            thought=thought,
            raw_response=result,
        )

        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        # TODO - why is this cast needed?
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
        """Create a stream of string chunks from the model ending with a :class:`~autogen_core.models.CreateResult`.

        Extends :meth:`autogen_core.models.ChatCompletionClient.create_stream` to support OpenAI API.

        In streaming, the default behaviour is not return token usage counts.
        See: `OpenAI API reference for possible args <https://platform.openai.com/docs/api-reference/chat/create>`_.

        You can set `extra_create_args={"stream_options": {"include_usage": True}}`
        (if supported by the accessed API) to
        return a final chunk with usage set to a :class:`~autogen_core.models.RequestUsage` object
        with prompt and completion token counts,
        all preceding chunks will have usage as `None`.
        See: `OpenAI API reference for stream options <https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream_options>`_.

        Other examples of supported arguments that can be included in `extra_create_args`:
            - `temperature` (float): Controls the randomness of the output. Higher values (e.g., 0.8) make the output more random, while lower values (e.g., 0.2) make it more focused and deterministic.
            - `max_tokens` (int): The maximum number of tokens to generate in the completion.
            - `top_p` (float): An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.
            - `frequency_penalty` (float): A value between -2.0 and 2.0 that penalizes new tokens based on their existing frequency in the text so far, decreasing the likelihood of repeated phrases.
            - `presence_penalty` (float): A value between -2.0 and 2.0 that penalizes new tokens based on whether they appear in the text so far, encouraging the model to talk about new topics.
        """

        create_params = self._process_create_args(
            messages,
            tools,
            json_output,
            extra_create_args,
        )

        if max_consecutive_empty_chunk_tolerance != 0:
            warnings.warn(
                "The 'max_consecutive_empty_chunk_tolerance' parameter is deprecated and will be removed in the future releases. All of empty chunks will be skipped with a warning.",
                DeprecationWarning,
                stacklevel=2,
            )

        if create_params.response_format is not None:
            chunks = self._create_stream_chunks_beta_client(
                tool_params=create_params.tools,
                oai_messages=create_params.messages,
                response_format=create_params.response_format,
                create_args_no_response_format=create_params.create_args,
                cancellation_token=cancellation_token,
            )
        else:
            chunks = self._create_stream_chunks(
                tool_params=create_params.tools,
                oai_messages=create_params.messages,
                create_args=create_params.create_args,
                cancellation_token=cancellation_token,
            )

        # Prepare data to process streaming chunks.
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], ChunkChoice] = cast(ChunkChoice, None)
        chunk = None
        stop_reason = None
        maybe_model = None
        content_deltas: List[str] = []
        thought_deltas: List[str] = []
        full_tool_calls: Dict[int, FunctionCall] = {}
        completion_tokens = 0
        logprobs: Optional[List[ChatCompletionTokenLogprob]] = None

        empty_chunk_warning_has_been_issued: bool = False
        empty_chunk_warning_threshold: int = 10
        empty_chunk_count = 0

        first_chunk = True

        # Process the stream of chunks.
        async for chunk in chunks:
            if first_chunk:
                first_chunk = False
                # Emit the start event.
                logger.info(
                    LLMStreamStartEvent(
                        messages=cast(List[Dict[str, Any]], create_params.messages),
                    )
                )
            # Empty chunks has been observed when the endpoint is under heavy load.
            #  https://github.com/microsoft/autogen/issues/4213
            if len(chunk.choices) == 0:
                empty_chunk_count += 1
                if not empty_chunk_warning_has_been_issued and empty_chunk_count >= empty_chunk_warning_threshold:
                    empty_chunk_warning_has_been_issued = True
                    warnings.warn(
                        f"Received more than {empty_chunk_warning_threshold} consecutive empty chunks. Empty chunks are being ignored.",
                        stacklevel=2,
                    )
                continue
            else:
                empty_chunk_count = 0

            # to process usage chunk in streaming situations
            # add    stream_options={"include_usage": True} in the initialization of OpenAIChatCompletionClient(...)
            # However the different api's
            # OPENAI api usage chunk produces no choices so need to check if there is a choice
            # liteLLM api usage chunk does produce choices
            choice = (
                chunk.choices[0]
                if len(chunk.choices) > 0
                else (choice if chunk.usage is not None and stop_reason is not None else cast(ChunkChoice, None))
            )

            # for liteLLM chunk usage, do the following hack keeping the pervious chunk.stop_reason (if set).
            # set the stop_reason for the usage chunk to the prior stop_reason
            stop_reason = choice.finish_reason if chunk.usage is None and stop_reason is None else stop_reason
            maybe_model = chunk.model
            # First try get content
            if choice.delta.content:
                content_deltas.append(choice.delta.content)
                if len(choice.delta.content) > 0:
                    yield choice.delta.content
                # NOTE: for OpenAI, tool_calls and content are mutually exclusive it seems, so we can skip the rest of the loop.
                # However, this may not be the case for other APIs -- we should expect this may need to be updated.
                continue
            # if there is a reasoning_content field, then we populate the thought field. This is for models such as R1.
            if choice.delta.model_extra is not None:
                reasoning_content = choice.delta.model_extra.get("reasoning_content")
                if reasoning_content is not None:
                    thought_deltas.append(reasoning_content)
                    yield reasoning_content
            # Otherwise, get tool calls
            if choice.delta.tool_calls is not None:
                for tool_call_chunk in choice.delta.tool_calls:
                    idx = tool_call_chunk.index
                    if idx not in full_tool_calls:
                        # We ignore the type hint here because we want to fill in type when the delta provides it
                        full_tool_calls[idx] = FunctionCall(id="", arguments="", name="")

                    if tool_call_chunk.id is not None:
                        full_tool_calls[idx].id += tool_call_chunk.id

                    if tool_call_chunk.function is not None:
                        if tool_call_chunk.function.name is not None:
                            full_tool_calls[idx].name += tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments is not None:
                            full_tool_calls[idx].arguments += tool_call_chunk.function.arguments
            if choice.logprobs and choice.logprobs.content:
                logprobs = [
                    ChatCompletionTokenLogprob(
                        token=x.token,
                        logprob=x.logprob,
                        top_logprobs=[TopLogprob(logprob=y.logprob, bytes=y.bytes) for y in x.top_logprobs],
                        bytes=x.bytes,
                    )
                    for x in choice.logprobs.content
                ]

        # Finalize the CreateResult.

        # TODO: can we remove this?
        if stop_reason == "function_call":
            raise ValueError("Function calls are not supported in this context")

        # We need to get the model from the last chunk, if available.
        model = maybe_model or create_params.create_args["model"]
        model = model.replace("gpt-35", "gpt-3.5")  # hack for Azure API

        # Because the usage chunk is not guaranteed to be the last chunk, we need to check if it is available.
        if chunk and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
        else:
            prompt_tokens = 0
            completion_tokens = 0
        usage = RequestUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # Detect whether it is a function call or just text.
        content: Union[str, List[FunctionCall]]
        thought: str | None = None
        # Determine the content and thought based on what was collected
        if full_tool_calls:
            # This is a tool call response
            content = list(full_tool_calls.values())
            if content_deltas:
                # Store any text alongside tool calls as thoughts
                thought = "".join(content_deltas)
        else:
            # This is a text response (possibly with thoughts)
            if content_deltas:
                content = "".join(content_deltas)
            else:
                warnings.warn(
                    "No text content or tool calls are available. Model returned empty result.",
                    stacklevel=2,
                )
                content = ""

        # Always set thoughts if we have any, regardless of other content types
        if thought_deltas:
            thought = "".join(thought_deltas)

        # This is for local R1 models.
        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1 and thought is None:
            thought, content = parse_r1_content(content)

        # Create the result.
        result = CreateResult(
            finish_reason=normalize_stop_reason(stop_reason),
            content=content,
            usage=usage,
            cached=False,
            logprobs=logprobs,
            thought=thought,
            raw_response=result,
        )

        # Log the end of the stream.
        logger.info(
            LLMStreamEndEvent(
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        # Update the total usage.
        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        # Yield the CreateResult.
        yield result

    async def _create_stream_chunks(
        self,
        tool_params: List[ChatCompletionToolParam],
        oai_messages: List[ChatCompletionMessageParam],
        create_args: Dict[str, Any],
        cancellation_token: Optional[CancellationToken],
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        stream_future = asyncio.ensure_future(
            self._client.chat.completions.create(
                messages=oai_messages,
                stream=True,
                tools=tool_params if len(tool_params) > 0 else NOT_GIVEN,
                **create_args,
            )
        )
        if cancellation_token is not None:
            cancellation_token.link_future(stream_future)
        stream = await stream_future
        while True:
            try:
                chunk_future = asyncio.ensure_future(anext(stream))
                if cancellation_token is not None:
                    cancellation_token.link_future(chunk_future)
                chunk = await chunk_future
                yield chunk
            except StopAsyncIteration:
                break

    async def _create_stream_chunks_beta_client(
        self,
        tool_params: List[ChatCompletionToolParam],
        oai_messages: List[ChatCompletionMessageParam],
        create_args_no_response_format: Dict[str, Any],
        response_format: Optional[Type[BaseModel]],
        cancellation_token: Optional[CancellationToken],
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        async with self._client.beta.chat.completions.stream(
            messages=oai_messages,
            tools=tool_params if len(tool_params) > 0 else NOT_GIVEN,
            response_format=(response_format if response_format is not None else NOT_GIVEN),
            **create_args_no_response_format,
        ) as stream:
            while True:
                try:
                    event_future = asyncio.ensure_future(anext(stream))
                    if cancellation_token is not None:
                        cancellation_token.link_future(event_future)
                    event = await event_future

                    if event.type == "chunk":
                        chunk = event.chunk
                        yield chunk
                    # We don't handle other event types from the beta client stream.
                    # As the other event types are auxiliary to the chunk event.
                    # See: https://github.com/openai/openai-python/blob/main/helpers.md#chat-completions-events.
                    # Once the beta client is stable, we can move all the logic to the beta client.
                    # Then we can consider handling other event types which may simplify the code overall.
                except StopAsyncIteration:
                    break

    async def close(self) -> None:
        await self._client.close()

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        model = self._create_args["model"]
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            trace_logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        tokens_per_message = 3
        tokens_per_name = 1
        num_tokens = 0

        # Message tokens.
        for message in messages:
            num_tokens += tokens_per_message
            oai_message = to_oai_type(message, prepend_name=self._add_name_prefixes)
            for oai_message_part in oai_message:
                for key, value in oai_message_part.items():
                    if value is None:
                        continue

                    if isinstance(message, UserMessage) and isinstance(value, list):
                        typed_message_value = cast(List[ChatCompletionContentPartParam], value)

                        assert len(typed_message_value) == len(
                            message.content
                        ), "Mismatch in message content and typed message value"

                        # We need image properties that are only in the original message
                        for part, content_part in zip(typed_message_value, message.content, strict=False):
                            if isinstance(content_part, Image):
                                # TODO: add detail parameter
                                num_tokens += calculate_vision_tokens(content_part)
                            elif isinstance(part, str):
                                num_tokens += len(encoding.encode(part))
                            else:
                                try:
                                    serialized_part = json.dumps(part)
                                    num_tokens += len(encoding.encode(serialized_part))
                                except TypeError:
                                    trace_logger.warning(f"Could not convert {part} to string, skipping.")
                    else:
                        if not isinstance(value, str):
                            try:
                                value = json.dumps(value)
                            except TypeError:
                                trace_logger.warning(f"Could not convert {value} to string, skipping.")
                                continue
                        num_tokens += len(encoding.encode(value))
                        if key == "name":
                            num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

        # Tool tokens.
        oai_tools = convert_tools(tools)
        for tool in oai_tools:
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
        warnings.warn(
            "capabilities is deprecated, use model_info instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._model_info

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info


class OpenAIChatCompletionClient(BaseOpenAIChatCompletionClient, Component[OpenAIClientConfigurationConfigModel]):
    """Chat completion client for OpenAI hosted models.

    To use this client, you must install the `openai` extra:

    .. code-block:: bash

        pip install "autogen-ext[openai]"

    You can also use this client for OpenAI-compatible ChatCompletion endpoints.
    **Using this client for non-OpenAI models is not tested or guaranteed.**

    For non-OpenAI models, please first take a look at our `community extensions <https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/index.html>`_
    for additional model clients.

    Args:
        model (str): Which OpenAI model to use.
        api_key (optional, str): The API key to use. **Required if 'OPENAI_API_KEY' is not found in the environment variables.**
        organization (optional, str): The organization ID to use.
        base_url (optional, str): The base URL to use. **Required if the model is not hosted on OpenAI.**
        timeout: (optional, float): The timeout for the request in seconds.
        max_retries (optional, int): The maximum number of retries to attempt.
        model_info (optional, ModelInfo): The capabilities of the model. **Required if the model name is not a valid OpenAI model.**
        frequency_penalty (optional, float):
        logit_bias: (optional, dict[str, int]):
        max_tokens (optional, int):
        n (optional, int):
        presence_penalty (optional, float):
        response_format (optional, Dict[str, Any]): the format of the response. Possible options are:

            .. code-block:: text

                # Text response, this is the default.
                {"type": "text"}

            .. code-block:: text

                # JSON response, make sure to instruct the model to return JSON.
                {"type": "json_object"}

            .. code-block:: text

                # Structured output response, with a pre-defined JSON schema.
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "name of the schema, must be an identifier.",
                        "description": "description for the model.",
                        # You can convert a Pydantic (v2) model to JSON schema
                        # using the `model_json_schema()` method.
                        "schema": "<the JSON schema itself>",
                        # Whether to enable strict schema adherence when
                        # generating the output. If set to true, the model will
                        # always follow the exact schema defined in the
                        # `schema` field. Only a subset of JSON Schema is
                        # supported when `strict` is `true`.
                        # To learn more, read
                        # https://platform.openai.com/docs/guides/structured-outputs.
                        "strict": False,  # or True
                    },
                }

            It is recommended to use the `json_output` parameter in
            :meth:`~autogen_ext.models.openai.BaseOpenAIChatCompletionClient.create` or
            :meth:`~autogen_ext.models.openai.BaseOpenAIChatCompletionClient.create_stream`
            methods instead of `response_format` for structured output.
            The `json_output` parameter is more flexible and allows you to
            specify a Pydantic model class directly.

        seed (optional, int):
        stop (optional, str | List[str]):
        temperature (optional, float):
        top_p (optional, float):
        user (optional, str):
        default_headers (optional, dict[str, str]):  Custom headers; useful for authentication or other custom requirements.
        add_name_prefixes (optional, bool): Whether to prepend the `source` value
            to each :class:`~autogen_core.models.UserMessage` content. E.g.,
            "this is content" becomes "Reviewer said: this is content."
            This can be useful for models that do not support the `name` field in
            message. Defaults to False.
        stream_options (optional, dict): Additional options for streaming. Currently only `include_usage` is supported.

    Examples:

        The following code snippet shows how to use the client with an OpenAI model:

        .. code-block:: python

            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_core.models import UserMessage

            openai_client = OpenAIChatCompletionClient(
                model="gpt-4o-2024-08-06",
                # api_key="sk-...", # Optional if you have an OPENAI_API_KEY environment variable set.
            )

            result = await openai_client.create([UserMessage(content="What is the capital of France?", source="user")])  # type: ignore
            print(result)

            # Close the client when done.
            # await openai_client.close()

        To use the client with a non-OpenAI model, you need to provide the base URL of the model and the model info.
        For example, to use Ollama, you can use the following code snippet:

        .. code-block:: python

            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_core.models import ModelFamily

            custom_model_client = OpenAIChatCompletionClient(
                model="deepseek-r1:1.5b",
                base_url="http://localhost:11434/v1",
                api_key="placeholder",
                model_info={
                    "vision": False,
                    "function_calling": False,
                    "json_output": False,
                    "family": ModelFamily.R1,
                    "structured_output": True,
                },
            )

            # Close the client when done.
            # await custom_model_client.close()

        To use streaming mode, you can use the following code snippet:

        .. code-block:: python

            import asyncio
            from autogen_core.models import UserMessage
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                # Similar for AzureOpenAIChatCompletionClient.
                model_client = OpenAIChatCompletionClient(model="gpt-4o")  # assuming OPENAI_API_KEY is set in the environment.

                messages = [UserMessage(content="Write a very short story about a dragon.", source="user")]

                # Create a stream.
                stream = model_client.create_stream(messages=messages)

                # Iterate over the stream and print the responses.
                print("Streamed responses:")
                async for response in stream:
                    if isinstance(response, str):
                        # A partial response is a string.
                        print(response, flush=True, end="")
                    else:
                        # The last response is a CreateResult object with the complete message.
                        print("\\n\\n------------\\n")
                        print("The complete response:", flush=True)
                        print(response.content, flush=True)

                # Close the client when done.
                await model_client.close()


            asyncio.run(main())

        To use structured output as well as function calling, you can use the following code snippet:

        .. code-block:: python

            import asyncio
            from typing import Literal

            from autogen_core.models import (
                AssistantMessage,
                FunctionExecutionResult,
                FunctionExecutionResultMessage,
                SystemMessage,
                UserMessage,
            )
            from autogen_core.tools import FunctionTool
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from pydantic import BaseModel


            # Define the structured output format.
            class AgentResponse(BaseModel):
                thoughts: str
                response: Literal["happy", "sad", "neutral"]


            # Define the function to be called as a tool.
            def sentiment_analysis(text: str) -> str:
                \"\"\"Given a text, return the sentiment.\"\"\"
                return "happy" if "happy" in text else "sad" if "sad" in text else "neutral"


            # Create a FunctionTool instance with `strict=True`,
            # which is required for structured output mode.
            tool = FunctionTool(sentiment_analysis, description="Sentiment Analysis", strict=True)


            async def main() -> None:
                # Create an OpenAIChatCompletionClient instance.
                model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

                # Generate a response using the tool.
                response1 = await model_client.create(
                    messages=[
                        SystemMessage(content="Analyze input text sentiment using the tool provided."),
                        UserMessage(content="I am happy.", source="user"),
                    ],
                    tools=[tool],
                )
                print(response1.content)
                # Should be a list of tool calls.
                # [FunctionCall(name="sentiment_analysis", arguments={"text": "I am happy."}, ...)]

                assert isinstance(response1.content, list)
                response2 = await model_client.create(
                    messages=[
                        SystemMessage(content="Analyze input text sentiment using the tool provided."),
                        UserMessage(content="I am happy.", source="user"),
                        AssistantMessage(content=response1.content, source="assistant"),
                        FunctionExecutionResultMessage(
                            content=[FunctionExecutionResult(content="happy", call_id=response1.content[0].id, is_error=False, name="sentiment_analysis")]
                        ),
                    ],
                    # Use the structured output format.
                    json_output=AgentResponse,
                )
                print(response2.content)
                # Should be a structured output.
                # {"thoughts": "The user is happy.", "response": "happy"}

                # Close the client when done.
                await model_client.close()

            asyncio.run(main())


        To load the client from a configuration, you can use the `load_component` method:

        .. code-block:: python

            from autogen_core.models import ChatCompletionClient

            config = {
                "provider": "OpenAIChatCompletionClient",
                "config": {"model": "gpt-4o", "api_key": "REPLACE_WITH_YOUR_API_KEY"},
            }

            client = ChatCompletionClient.load_component(config)

        To view the full list of available configuration options, see the :py:class:`OpenAIClientConfigurationConfigModel` class.

    """

    component_type = "model"
    component_config_schema = OpenAIClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.openai.OpenAIChatCompletionClient"

    def __init__(self, **kwargs: Unpack[OpenAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OpenAIChatCompletionClient")

        model_capabilities: Optional[ModelCapabilities] = None  # type: ignore
        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        add_name_prefixes: bool = False
        if "add_name_prefixes" in kwargs:
            add_name_prefixes = kwargs["add_name_prefixes"]

        # Special handling for Gemini model.
        assert "model" in copied_args and isinstance(copied_args["model"], str)
        if copied_args["model"].startswith("gemini-"):
            if "base_url" not in copied_args:
                copied_args["base_url"] = _model_info.GEMINI_OPENAI_BASE_URL
            if "api_key" not in copied_args and "GEMINI_API_KEY" in os.environ:
                copied_args["api_key"] = os.environ["GEMINI_API_KEY"]

        client = _openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)

        super().__init__(
            client=client,
            create_args=create_args,
            model_capabilities=model_capabilities,
            model_info=model_info,
            add_name_prefixes=add_name_prefixes,
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _openai_client_from_config(state["_raw_config"])

    def _to_config(self) -> OpenAIClientConfigurationConfigModel:
        copied_config = self._raw_config.copy()
        return OpenAIClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: OpenAIClientConfigurationConfigModel) -> Self:
        copied_config = config.model_copy().model_dump(exclude_none=True)

        # Handle api_key as SecretStr
        if "api_key" in copied_config and isinstance(config.api_key, SecretStr):
            copied_config["api_key"] = config.api_key.get_secret_value()

        return cls(**copied_config)


class AzureOpenAIChatCompletionClient(
    BaseOpenAIChatCompletionClient, Component[AzureOpenAIClientConfigurationConfigModel]
):
    """Chat completion client for Azure OpenAI hosted models.

    To use this client, you must install the `azure` and `openai` extensions:

    .. code-block:: bash

        pip install "autogen-ext[openai,azure]"

    Args:

        model (str): Which OpenAI model to use.
        azure_endpoint (str): The endpoint for the Azure model. **Required for Azure models.**
        azure_deployment (str): Deployment name for the Azure model. **Required for Azure models.**
        api_version (str): The API version to use. **Required for Azure models.**
        azure_ad_token (str): The Azure AD token to use. Provide this or `azure_ad_token_provider` for token-based authentication.
        azure_ad_token_provider (optional, Callable[[], Awaitable[str]] | AzureTokenProvider): The Azure AD token provider to use. Provide this or `azure_ad_token` for token-based authentication.
        api_key (optional, str): The API key to use, use this if you are using key based authentication. It is optional if you are using Azure AD token based authentication or `AZURE_OPENAI_API_KEY` environment variable.
        timeout: (optional, float): The timeout for the request in seconds.
        max_retries (optional, int): The maximum number of retries to attempt.
        model_info (optional, ModelInfo): The capabilities of the model. **Required if the model name is not a valid OpenAI model.**
        frequency_penalty (optional, float):
        logit_bias: (optional, dict[str, int]):
        max_tokens (optional, int):
        n (optional, int):
        presence_penalty (optional, float):
        response_format (optional, Dict[str, Any]): the format of the response. Possible options are:

            .. code-block:: text

                # Text response, this is the default.
                {"type": "text"}

            .. code-block:: text

                # JSON response, make sure to instruct the model to return JSON.
                {"type": "json_object"}

            .. code-block:: text

                # Structured output response, with a pre-defined JSON schema.
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "name of the schema, must be an identifier.",
                        "description": "description for the model.",
                        # You can convert a Pydantic (v2) model to JSON schema
                        # using the `model_json_schema()` method.
                        "schema": "<the JSON schema itself>",
                        # Whether to enable strict schema adherence when
                        # generating the output. If set to true, the model will
                        # always follow the exact schema defined in the
                        # `schema` field. Only a subset of JSON Schema is
                        # supported when `strict` is `true`.
                        # To learn more, read
                        # https://platform.openai.com/docs/guides/structured-outputs.
                        "strict": False,  # or True
                    },
                }

            It is recommended to use the `json_output` parameter in
            :meth:`~autogen_ext.models.openai.BaseOpenAIChatCompletionClient.create` or
            :meth:`~autogen_ext.models.openai.BaseOpenAIChatCompletionClient.create_stream`
            methods instead of `response_format` for structured output.
            The `json_output` parameter is more flexible and allows you to
            specify a Pydantic model class directly.

        seed (optional, int):
        stop (optional, str | List[str]):
        temperature (optional, float):
        top_p (optional, float):
        user (optional, str):
        default_headers (optional, dict[str, str]):  Custom headers; useful for authentication or other custom requirements.


    To use the client, you need to provide your deployment name, Azure Cognitive Services endpoint, and api version.
    For authentication, you can either provide an API key or an Azure Active Directory (AAD) token credential.

    The following code snippet shows how to use AAD authentication.
    The identity used must be assigned the `Cognitive Services OpenAI User <https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/role-based-access-control#cognitive-services-openai-user>`_ role.

    .. code-block:: python

        from autogen_ext.auth.azure import AzureTokenProvider
        from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
        from azure.identity import DefaultAzureCredential

        # Create the token provider
        token_provider = AzureTokenProvider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

        az_model_client = AzureOpenAIChatCompletionClient(
            azure_deployment="{your-azure-deployment}",
            model="{model-name, such as gpt-4o}",
            api_version="2024-06-01",
            azure_endpoint="https://{your-custom-endpoint}.openai.azure.com/",
            azure_ad_token_provider=token_provider,  # Optional if you choose key-based authentication.
            # api_key="sk-...", # For key-based authentication.
        )

    See other usage examples in the :class:`OpenAIChatCompletionClient` class.

    To load the client that uses identity based aith from a configuration, you can use the `load_component` method:

    .. code-block:: python

        from autogen_core.models import ChatCompletionClient

        config = {
            "provider": "AzureOpenAIChatCompletionClient",
            "config": {
                "model": "gpt-4o-2024-05-13",
                "azure_endpoint": "https://{your-custom-endpoint}.openai.azure.com/",
                "azure_deployment": "{your-azure-deployment}",
                "api_version": "2024-06-01",
                "azure_ad_token_provider": {
                    "provider": "autogen_ext.auth.azure.AzureTokenProvider",
                    "config": {
                        "provider_kind": "DefaultAzureCredential",
                        "scopes": ["https://cognitiveservices.azure.com/.default"],
                    },
                },
            },
        }

        client = ChatCompletionClient.load_component(config)


    To view the full list of available configuration options, see the :py:class:`AzureOpenAIClientConfigurationConfigModel` class.

    .. note::

        Right now only `DefaultAzureCredential` is supported with no additional args passed to it.

    See `here <https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/managed-identity#chat-completions>`_ for how to use the Azure client directly or for more info.

    """

    component_type = "model"
    component_config_schema = AzureOpenAIClientConfigurationConfigModel
    component_provider_override = "autogen_ext.models.openai.AzureOpenAIChatCompletionClient"

    def __init__(self, **kwargs: Unpack[AzureOpenAIClientConfiguration]):
        model_capabilities: Optional[ModelCapabilities] = None  # type: ignore
        copied_args = dict(kwargs).copy()
        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        add_name_prefixes: bool = False
        if "add_name_prefixes" in kwargs:
            add_name_prefixes = kwargs["add_name_prefixes"]

        client = _azure_openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)
        self._raw_config: Dict[str, Any] = copied_args
        super().__init__(
            client=client,
            create_args=create_args,
            model_capabilities=model_capabilities,
            model_info=model_info,
            add_name_prefixes=add_name_prefixes,
        )

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _azure_openai_client_from_config(state["_raw_config"])

    def _to_config(self) -> AzureOpenAIClientConfigurationConfigModel:
        from ...auth.azure import AzureTokenProvider

        copied_config = self._raw_config.copy()
        if "azure_ad_token_provider" in copied_config:
            if not isinstance(copied_config["azure_ad_token_provider"], AzureTokenProvider):
                raise ValueError("azure_ad_token_provider must be a AzureTokenProvider to be component serialized")

            copied_config["azure_ad_token_provider"] = (
                copied_config["azure_ad_token_provider"].dump_component().model_dump(exclude_none=True)
            )

        return AzureOpenAIClientConfigurationConfigModel(**copied_config)

    @classmethod
    def _from_config(cls, config: AzureOpenAIClientConfigurationConfigModel) -> Self:
        from ...auth.azure import AzureTokenProvider

        copied_config = config.model_copy().model_dump(exclude_none=True)

        # Handle api_key as SecretStr
        if "api_key" in copied_config and isinstance(config.api_key, SecretStr):
            copied_config["api_key"] = config.api_key.get_secret_value()

        if "azure_ad_token_provider" in copied_config:
            copied_config["azure_ad_token_provider"] = AzureTokenProvider.load_component(
                copied_config["azure_ad_token_provider"]
            )

        return cls(**copied_config)
