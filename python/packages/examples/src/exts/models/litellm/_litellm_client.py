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
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.shared_params import FunctionDefinition, FunctionParameters
from pydantic import BaseModel
from typing_extensions import Unpack

from autogen_core.application.logging import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from autogen_core.application.logging.events import LLMCallEvent
from autogen_core.base import CancellationToken
from autogen_core.components import (
    FunctionCall,
    Image,
)
from autogen_core.components.tools import Tool, ToolSchema
from autogen_core.components.models._model_client import ChatCompletionClient, ModelCapabilities
from autogen_core.components.models._types import (
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
from litellm import acompletion as litellm_achat
from ._provider_infos import is_not_support_user_message_name
import litellm

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


create_kwargs = set(completion_create_params.CompletionCreateParamsBase.__annotations__.keys()) | set(
    ("timeout", "stream")
)
# Only single choice allowed
disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
required_create_args: Set[str] = set(["model"])

DEFUALT_TOKEN_LIMIT=81920

def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in create_kwargs}
    create_args_keys = set(create_args.keys())
    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")
    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")
    return create_args

def type_to_role(message: LLMMessage) -> ChatCompletionRole:
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    else:
        return "tool"


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


class LiteLlmChatCompletionClient(ChatCompletionClient):
    def __init__(
        self,
        provider: str,
        model:str,
        **create_args
        
    ):
        self._provider = provider
        self._model = provider+"/"+model if provider else model
        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return LiteLlmChatCompletionClient(**config)
    
    def user_message_to_oai(self,message: UserMessage) -> ChatCompletionUserMessageParam:
        if message.source:
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


    def system_message_to_oai(self,message: SystemMessage) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(
            content=message.content,
            role="system",
        )


    def func_call_to_oai(self,message: FunctionCall) -> ChatCompletionMessageToolCallParam:
        return ChatCompletionMessageToolCallParam(
            id=message.id,
            function={
                "arguments": message.arguments,
                "name": message.name,
            },
            type="function",
        )


    def tool_message_to_oai(self,
        message: FunctionExecutionResultMessage,
    ) -> Sequence[ChatCompletionToolMessageParam]:
        return [
            ChatCompletionToolMessageParam(content=x.content, role="tool", tool_call_id=x.call_id) for x in message.content
        ]


    def assistant_message_to_oai(self,
        message: AssistantMessage,
    ) -> ChatCompletionAssistantMessageParam:
        assert_valid_name(message.source)
        if isinstance(message.content, list):
            return ChatCompletionAssistantMessageParam(
                tool_calls=[self.func_call_to_oai(x) for x in message.content],
                role="assistant",
                name=message.source,
            )
        else:
            return ChatCompletionAssistantMessageParam(
                content=message.content,
                role="assistant",
                name=message.source,
            )
    
    def to_oai_type(self,message: LLMMessage) -> Sequence[ChatCompletionMessageParam]:
        if isinstance(message, SystemMessage):
            return [self.system_message_to_oai(message)]
        elif isinstance(message, UserMessage):
            user_msg = self.user_message_to_oai(message)
            if is_not_support_user_message_name(self._provider):
                del user_msg['name']
            return [user_msg]

        elif isinstance(message, AssistantMessage):
            assistant_msg = self.assistant_message_to_oai(message)
            if is_not_support_user_message_name(self._provider):
                del assistant_msg['name']
            return [assistant_msg]
        else:
            return self.tool_message_to_oai(message)

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

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        oai_messages_nested = [self.to_oai_type(m) for m in messages]
        oai_messages = [item for sublist in oai_messages_nested for item in sublist]

        future: Union[Task[ParsedChatCompletion[BaseModel]], Task[ChatCompletion]]
        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            if use_beta_client:
                # Pass response_format_value if it's not None
                if response_format_value is not None:
                    future = asyncio.ensure_future(
                        litellm_achat(
                            model=self._model,
                            messages=oai_messages,
                            tools=converted_tools,
                            response_format=response_format_value,
                            **create_args_no_response_format,
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        litellm_achat(
                            model=self._model,
                            messages=oai_messages,
                            tools=converted_tools,
                            **create_args_no_response_format,
                        )
                    )
            else:
                future = asyncio.ensure_future(
                    litellm_achat(
                            model=self._model,
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
                        litellm_achat(
                            model=self._model,
                            messages=oai_messages,
                            response_format=response_format_value,
                            **create_args_no_response_format,
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        litellm_achat(
                            model=self._model,
                            messages=oai_messages,
                            **create_args_no_response_format,
                        )
                    )
            else:
                future = asyncio.ensure_future(
                    litellm_achat(
                        model=self._model,
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

        # Limited to a single choice currently.
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], Choice] = result.choices[0]
        if choice.finish_reason == "function_call":
            raise ValueError("Function calls are not supported in this context")

        content: Union[str, List[FunctionCall]]

       # if choice.finish_reason == "tool_calls":
       # 非openai的接口，它finish_reason有可能是stop的：
        if getattr(choice.message,"tool_calls",None):

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
        if getattr(choice,"logprobs",None) and choice.logprobs.content:
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
        """
        Creates an AsyncGenerator that will yield a stream of chat completions based on the provided messages and tools.

        Args:
            messages (Sequence[LLMMessage]): A sequence of messages to be processed.
            tools (Sequence[Tool | ToolSchema], optional): A sequence of tools to be used in the completion. Defaults to `[]`.
            json_output (Optional[bool], optional): If True, the output will be in JSON format. Defaults to None.
            extra_create_args (Mapping[str, Any], optional): Additional arguments for the creation process. Default to `{}`.
            cancellation_token (Optional[CancellationToken], optional): A token to cancel the operation. Defaults to None.

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
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        oai_messages_nested = [self.to_oai_type(m) for m in messages]
        oai_messages = [item for sublist in oai_messages_nested for item in sublist]
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
                litellm_achat(
                            model=self._model,messages=oai_messages, stream=True, **create_args)
            )
        if cancellation_token is not None:
            cancellation_token.link_future(stream_future)
        stream = await stream_future
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], ChunkChoice] = cast(ChunkChoice, None)
        chunk = None
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

                # to process usage chunk in streaming situations
                # add    stream_options={"include_usage": True} in the initialization of OpenAIChatCompletionClient(...)
                # However the different api's
                # OPENAI api usage chunk produces no choices so need to check if there is a choice
                # liteLLM api usage chunk does produce choices
                choice = (
                    chunk.choices[0]
                    if len(chunk.choices) > 0
                    else choice
                    if chunk.usage is not None and stop_reason is not None
                    else cast(ChunkChoice, None)
                )

                # for liteLLM chunk usage, do the following hack keeping the pervious chunk.stop_reason (if set).
                # set the stop_reason for the usage chunk to the prior stop_reason
                stop_reason = choice.finish_reason if chunk.usage is None and stop_reason is None else stop_reason
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

        if chunk and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
        else:
            prompt_tokens = 0

        if stop_reason is None:
            raise ValueError("No stop reason found")

        content: Union[str, List[FunctionCall]]
        if len(content_deltas) > 1:
            content = "".join(content_deltas)
            if chunk and chunk.usage:
                completion_tokens = chunk.usage.completion_tokens
            else:
                completion_tokens = 0
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
            oai_message = self.to_oai_type(message)
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
        return DEFUALT_TOKEN_LIMIT - self.count_tokens(messages, tools)
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(vision=False,function_calling=True,json_output=True)
   
