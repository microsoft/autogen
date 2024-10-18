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
    Set,
    Type,
    Union,
    cast,
)

import tiktoken
from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
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
from openai.types.shared_params import FunctionDefinition, FunctionParameters
from pydantic import BaseModel
from typing_extensions import Unpack

from ...application.logging import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from ...application.logging.events import LLMCallEvent
from ...base import CancellationToken
from .. import (
    FunctionCall,
    Image,
)
from ..tools import Tool, ToolSchema
from . import _model_info
from ._model_client import ChatCompletionClient, ModelCapabilities
from ._types import (
    AssistantMessage,
    ChatCompletionTokenLogprob,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
)
from .config import AzureOpenAIClientConfiguration, OpenAIClientConfiguration

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

    # Do some fixups
    copied_config["azure_deployment"] = copied_config.get("azure_deployment", config.get("model"))
    if copied_config["azure_deployment"] is not None:
        copied_config["azure_deployment"] = copied_config["azure_deployment"].replace(".", "")
    copied_config["azure_endpoint"] = copied_config.get("azure_endpoint", copied_config.pop("base_url", None))

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


def user_message_to_oai(message: UserMessage) -> ChatCompletionUserMessageParam:
    assert_valid_name(message.source)
    if isinstance(message.content, str):
        return ChatCompletionUserMessageParam(
            content=message.content,
            role="user",
            name=message.source,
        )
    else:
        parts: List[ChatCompletionContentPartParam] = []
        for part in message.content:
            if isinstance(part, str):
                oai_part = ChatCompletionContentPartTextParam(
                    text=part,
                    type="text",
                )
                parts.append(oai_part)
            elif isinstance(part, Image):
                # TODO: support url based images
                # TODO: support specifying details
                parts.append(part.to_openai_format())
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


def to_oai_type(message: LLMMessage) -> Sequence[ChatCompletionMessageParam]:
    if isinstance(message, SystemMessage):
        return [system_message_to_oai(message)]
    elif isinstance(message, UserMessage):
        return [user_message_to_oai(message)]
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


class BaseOpenAIChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        create_args: Dict[str, Any],
        model_capabilities: Optional[ModelCapabilities] = None,
    ):
        self._client = client
        if model_capabilities is None and isinstance(client, AsyncAzureOpenAI):
            raise ValueError("AzureOpenAIChatCompletionClient requires explicit model capabilities")
        elif model_capabilities is None:
            self._model_capabilities = _model_info.get_capabilties(create_args["model"])
        else:
            self._model_capabilities = model_capabilities

        self._resolved_model: Optional[str] = None
        if "model" in create_args:
            self._resolved_model = _model_info.resolve_model(create_args["model"])

        if (
            "response_format" in create_args
            and create_args["response_format"]["type"] == "json_object"
            and not self._model_capabilities["json_output"]
        ):
            raise ValueError("Model does not support JSON output")

        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(**config)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # Declare use_beta_client
        use_beta_client: bool = False
        response_format_value: Optional[Type[BaseModel]] = None

        if "response_format" in create_args:
            value = create_args["response_format"]
            # If value is a Pydantic model class, use the beta client
            if isinstance(value, type) and issubclass(value, BaseModel):
                response_format_value = value
                use_beta_client = True
            else:
                # response_format_value is not a Pydantic model class
                use_beta_client = False
                response_format_value = None

        # Remove 'response_format' from create_args to prevent passing it twice
        create_args_no_response_format = {k: v for k, v in create_args.items() if k != "response_format"}

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.capabilities["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        if self.capabilities["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output")

        oai_messages_nested = [to_oai_type(m) for m in messages]
        oai_messages = [item for sublist in oai_messages_nested for item in sublist]

        if self.capabilities["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")
        future: Union[Task[ParsedChatCompletion[BaseModel]], Task[ChatCompletion]]
        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            if use_beta_client:
                # Pass response_format_value if it's not None
                if response_format_value is not None:
                    future = asyncio.ensure_future(
                        self._client.beta.chat.completions.parse(
                            messages=oai_messages,
                            tools=converted_tools,
                            response_format=response_format_value,
                            **create_args_no_response_format,
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        self._client.beta.chat.completions.parse(
                            messages=oai_messages,
                            tools=converted_tools,
                            **create_args_no_response_format,
                        )
                    )
            else:
                future = asyncio.ensure_future(
                    self._client.chat.completions.create(
                        messages=oai_messages,
                        stream=False,
                        tools=converted_tools,
                        **create_args,
                    )
                )
        else:
            if use_beta_client:
                if response_format_value is not None:
                    future = asyncio.ensure_future(
                        self._client.beta.chat.completions.parse(
                            messages=oai_messages,
                            response_format=response_format_value,
                            **create_args_no_response_format,
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        self._client.beta.chat.completions.parse(
                            messages=oai_messages,
                            **create_args_no_response_format,
                        )
                    )
            else:
                future = asyncio.ensure_future(
                    self._client.chat.completions.create(
                        messages=oai_messages,
                        stream=False,
                        **create_args,
                    )
                )

        if cancellation_token is not None:
            cancellation_token.link_future(future)
        result: Union[ParsedChatCompletion[BaseModel], ChatCompletion] = await future
        if use_beta_client:
            result = cast(ParsedChatCompletion[Any], result)

        if result.usage is not None:
            logger.info(
                LLMCallEvent(
                    prompt_tokens=result.usage.prompt_tokens,
                    completion_tokens=result.usage.completion_tokens,
                )
            )

        usage = RequestUsage(
            # TODO backup token counting
            prompt_tokens=result.usage.prompt_tokens if result.usage is not None else 0,
            completion_tokens=(result.usage.completion_tokens if result.usage is not None else 0),
        )

        if self._resolved_model is not None:
            if self._resolved_model != result.model:
                warnings.warn(
                    f"Resolved model mismatch: {self._resolved_model} != {result.model}. Model mapping may be incorrect.",
                    stacklevel=2,
                )

        # Limited to a single choice currently.
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], Choice] = result.choices[0]
        if choice.finish_reason == "function_call":
            raise ValueError("Function calls are not supported in this context")

        content: Union[str, List[FunctionCall]]
        if choice.finish_reason == "tool_calls":
            assert choice.message.tool_calls is not None
            assert choice.message.function_call is None

            # NOTE: If OAI response type changes, this will need to be updated
            content = [
                FunctionCall(
                    id=x.id,
                    arguments=x.function.arguments,
                    name=normalize_name(x.function.name),
                )
                for x in choice.message.tool_calls
            ]
            finish_reason = "function_calls"
        else:
            finish_reason = choice.finish_reason
            content = choice.message.content or ""
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
        response = CreateResult(
            finish_reason=finish_reason,  # type: ignore
            content=content,
            usage=usage,
            cached=False,
            logprobs=logprobs,
        )

        _add_usage(self._actual_usage, usage)
        _add_usage(self._total_usage, usage)

        # TODO - why is this cast needed?
        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        oai_messages_nested = [to_oai_type(m) for m in messages]
        oai_messages = [item for sublist in oai_messages_nested for item in sublist]

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.capabilities["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            stream_future = asyncio.ensure_future(
                self._client.chat.completions.create(
                    messages=oai_messages,
                    stream=True,
                    tools=converted_tools,
                    **create_args,
                )
            )
        else:
            stream_future = asyncio.ensure_future(
                self._client.chat.completions.create(messages=oai_messages, stream=True, **create_args)
            )
        if cancellation_token is not None:
            cancellation_token.link_future(stream_future)
        stream = await stream_future

        stop_reason = None
        maybe_model = None
        content_deltas: List[str] = []
        full_tool_calls: Dict[int, FunctionCall] = {}
        completion_tokens = 0
        logprobs: Optional[List[ChatCompletionTokenLogprob]] = None
        while True:
            try:
                chunk_future = asyncio.ensure_future(anext(stream))
                if cancellation_token is not None:
                    cancellation_token.link_future(chunk_future)
                chunk = await chunk_future
                choice = chunk.choices[0]
                stop_reason = choice.finish_reason
                maybe_model = chunk.model
                # First try get content
                if choice.delta.content is not None:
                    content_deltas.append(choice.delta.content)
                    if len(choice.delta.content) > 0:
                        yield choice.delta.content
                    continue

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

            except StopAsyncIteration:
                break

        model = maybe_model or create_args["model"]
        model = model.replace("gpt-35", "gpt-3.5")  # hack for Azure API

        # TODO fix count token
        prompt_tokens = 0
        # prompt_tokens = count_token(messages, model=model)
        if stop_reason is None:
            raise ValueError("No stop reason found")

        content: Union[str, List[FunctionCall]]
        if len(content_deltas) > 1:
            content = "".join(content_deltas)
            completion_tokens = 0
            # completion_tokens = count_token(content, model=model)
        else:
            completion_tokens = 0
            # TODO: fix assumption that dict values were added in order and actually order by int index
            # for tool_call in full_tool_calls.values():
            #     # value = json.dumps(tool_call)
            #     # completion_tokens += count_token(value, model=model)
            #     completion_tokens += 0
            content = list(full_tool_calls.values())

        usage = RequestUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        if stop_reason == "function_call":
            raise ValueError("Function calls are not supported in this context")
        if stop_reason == "tool_calls":
            stop_reason = "function_calls"

        result = CreateResult(
            finish_reason=stop_reason,  # type: ignore
            content=content,
            usage=usage,
            cached=False,
            logprobs=logprobs,
        )

        _add_usage(self._actual_usage, usage)
        _add_usage(self._total_usage, usage)

        yield result

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
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
            oai_message = to_oai_type(message)
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

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        token_limit = _model_info.get_token_limit(self._create_args["model"])
        return token_limit - self.count_tokens(messages, tools)

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._model_capabilities


class OpenAIChatCompletionClient(BaseOpenAIChatCompletionClient):
    def __init__(self, **kwargs: Unpack[OpenAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OpenAIChatCompletionClient")

        model_capabilities: Optional[ModelCapabilities] = None
        copied_args = dict(kwargs).copy()
        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        client = _openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)
        self._raw_config = copied_args
        super().__init__(client, create_args, model_capabilities)

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _openai_client_from_config(state["_raw_config"])


class AzureOpenAIChatCompletionClient(BaseOpenAIChatCompletionClient):
    def __init__(self, **kwargs: Unpack[AzureOpenAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OpenAIChatCompletionClient")

        model_capabilities: Optional[ModelCapabilities] = None
        copied_args = dict(kwargs).copy()
        if "model_capabilities" in kwargs:
            model_capabilities = kwargs["model_capabilities"]
            del copied_args["model_capabilities"]

        client = _azure_openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)
        self._raw_config = copied_args
        super().__init__(client, create_args, model_capabilities)

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._client = _azure_openai_client_from_config(state["_raw_config"])
