import inspect
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union, cast
from openai import AsyncOpenAI, AsyncAzureOpenAI
from typing_extensions import Self
from jsonschema import validate

from ..._pydantic import type2schema
from ...cache import AbstractCache
from .base import ChatModelClient
from ...token_count_utils import count_token
from ..types import ChatMessage, CreateResponse, Function, RequestUsage, ToolCall
from ...oai.openai_utils import OAI_PRICE1K, get_key

from openai.types.chat import completion_create_params

from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessageParam,
)
from openai.types.chat import ChatCompletion

openai_init_kwargs = set(inspect.getfullargspec(AsyncOpenAI.__init__).kwonlyargs)
aopenai_init_kwargs = set(inspect.getfullargspec(AsyncAzureOpenAI.__init__).kwonlyargs)

create_kwargs = set(completion_create_params.CompletionCreateParamsBase.__annotations__.keys()) | set(
    ("timeout", "stream")
)
# Only single choice allowed
disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
required_create_args = set(["model"])


def _openai_client_from_config(config: Dict[str, Any]) -> Union[AsyncOpenAI, AsyncAzureOpenAI]:
    if config["api_type"] is not None and config["api_type"].startswith("azure"):
        # Take a copy
        copied_config = config.copy()

        # Do some fixups
        copied_config["azure_deployment"] = copied_config.get("azure_deployment", config.get("model"))
        if copied_config["azure_deployment"] is not None:
            copied_config["azure_deployment"] = copied_config["azure_deployment"].replace(".", "")
        copied_config["azure_endpoint"] = copied_config.get("azure_endpoint", copied_config.pop("base_url", None))

        # Shave down the config to just the AzureOpenAI kwargs
        azure_config = {k: v for k, v in copied_config.items() if k in aopenai_init_kwargs}
        return AsyncAzureOpenAI(**azure_config)
    else:
        # Shave down the config to just the OpenAI kwargs
        openai_config = {k: v for k, v in config.items() if k in openai_init_kwargs}
        return AsyncOpenAI(**openai_config)


def _create_args_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in create_kwargs}
    create_args_keys = set(create_args.keys())
    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")
    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")
    return create_args


oai_system_message_schema = type2schema(ChatCompletionSystemMessageParam)
oai_user_message_schema = type2schema(ChatCompletionUserMessageParam)
oai_assistant_message_schema = type2schema(ChatCompletionAssistantMessageParam)
oai_tool_message_schema = type2schema(ChatCompletionToolMessageParam)


# TODO: these should additionally disallow additional properties
def to_oai_type(message: ChatMessage) -> ChatCompletionMessageParam:
    if "role" in message:
        role = message["role"]
        if role == "system":
            validate(message, oai_system_message_schema)
            return cast(ChatCompletionSystemMessageParam, message)
        elif role == "user":
            validate(message, oai_user_message_schema)
            return cast(ChatCompletionUserMessageParam, message)
        elif role == "assistant":
            validate(message, oai_assistant_message_schema)
            return cast(ChatCompletionAssistantMessageParam, message)
        elif role == "tool":
            validate(message, oai_tool_message_schema)
            return cast(ChatCompletionToolMessageParam, message)
        else:
            raise ValueError(f"Invalid role: {role}")
    else:
        raise ValueError(f"Invalid message: {message}")


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    if usage1["cost"] is not None or usage2["cost"] is not None:
        cost = 0.0
        if usage1["cost"] is not None:
            cost += usage1["cost"]

        if usage2["cost"] is not None:
            cost += usage2["cost"]
    else:
        cost = None

    return RequestUsage(
        prompt_tokens=usage1["prompt_tokens"] + usage2["prompt_tokens"],
        completion_tokens=usage1["completion_tokens"] + usage2["completion_tokens"],
        cost=cost,
    )


def _cost(response: Union[ChatCompletion, Tuple[str, int, int]]) -> float:
    if isinstance(response, ChatCompletion):
        return _cost(
            (
                response.model,
                response.usage.prompt_tokens if response.usage is not None else 0,
                response.usage.completion_tokens if response.usage is not None else 0,
            )
        )

    """Calculate the cost of the response."""
    model, n_input_tokens, n_output_tokens = response

    if model not in OAI_PRICE1K:
        # TODO: add logging to warn that the model is not found
        # logger.debug(f"Model {model} is not found. The cost will be 0.", exc_info=True)
        return 0

    tmp_price1K = cast(Union[float, Tuple[float, float]], OAI_PRICE1K[model])
    # First value is input token rate, second value is output token rate
    if isinstance(tmp_price1K, tuple):
        return (tmp_price1K[0] * n_input_tokens + tmp_price1K[1] * n_output_tokens) / 1000
    return tmp_price1K * (n_input_tokens + n_output_tokens) / 1000


class OpenAIChatModelClient(ChatModelClient):
    def __init__(self, client: Union[AsyncOpenAI, AsyncAzureOpenAI], create_args: Dict[str, Any]) -> None:
        self._client = client
        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0, cost=0.0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0, cost=0.0)

    @classmethod
    def create_from_config(cls, config: Dict[str, str]) -> Self:
        client = _openai_client_from_config(config)
        create_args = _create_args_from_config(config)
        return cls(client, create_args)

    async def create(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> CreateResponse:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        if cache is not None:
            cache_key = get_key({**create_args, "messages": messages})
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                response = cast(CreateResponse, cached_value)
                response["cached"] = True
                _add_usage(self._total_usage, response["usage"])
                return response

        oai_messages = [to_oai_type(m) for m in messages]

        result = await self._client.chat.completions.create(messages=oai_messages, stream=False, **create_args)

        usage = RequestUsage(
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
            cost=_cost(result),
        )

        # Limited to a single choice currently.
        choice = result.choices[0]
        content: Union[str, List[ToolCall]]
        if choice.finish_reason == "tool_calls":
            assert choice.message.tool_calls is not None
            assert choice.message.function_call is None

            # NOTE: If OAI response type changes, this will need to be updated
            tool_calls = [x.model_dump() for x in choice.message.tool_calls]
            content = tool_calls
        else:
            content = choice.message.content or ""

        result = CreateResponse(finish_reason=choice.finish_reason, content=content, usage=usage, cached=False)

        if cache is not None:
            cache.set(cache_key, result)

        _add_usage(self._actual_usage, usage)
        _add_usage(self._total_usage, usage)

        # TODO - why is this cast needed?
        return cast(CreateResponse, result)

    async def create_stream(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> AsyncGenerator[Union[str, CreateResponse], None]:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        if cache is not None:
            cache_key = get_key({**create_args, "messages": messages})
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                response = cast(CreateResponse, cached_value)
                response["cached"] = True
                _add_usage(self._total_usage, response["usage"])
                yield response

        oai_messages = [to_oai_type(m) for m in messages]

        stream = await self._client.chat.completions.create(messages=oai_messages, stream=True, **create_args)

        stop_reason = None
        maybe_model = None
        content_deltas = []
        full_tool_calls: Dict[int, ToolCall] = {}
        completion_tokens = 0

        async for chunk in stream:
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
                        full_tool_calls[idx] = ToolCall(id="", function=Function(name="", arguments=""), type="")  # type: ignore[typeddict-item]

                    if tool_call_chunk.id is not None:
                        full_tool_calls[idx]["id"] += tool_call_chunk.id

                    if tool_call_chunk.type is not None:
                        full_tool_calls[idx]["type"] += tool_call_chunk.type

                    if tool_call_chunk.function is not None:
                        if tool_call_chunk.function.name is not None:
                            full_tool_calls[idx]["function"]["name"] += tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments is not None:
                            full_tool_calls[idx]["function"]["arguments"] += tool_call_chunk.function.arguments

        model = maybe_model or create_args["model"]
        model = model.replace("gpt-35", "gpt-3.5")  # hack for Azure API

        prompt_tokens = count_token(messages, model=model)
        if stop_reason is None:
            raise ValueError("No stop reason found")

        content: Union[str, List[ToolCall]]
        if len(content_deltas) > 1:
            content = "".join(content_deltas)
            completion_tokens = count_token(content, model=model)
        else:
            completion_tokens = 0
            # TODO: fix assumption that dict values were added in order and actually order by int index
            for tool_call in full_tool_calls.values():
                value = json.dumps(tool_call)
                completion_tokens += count_token(value, model=model)
            content = list(full_tool_calls.values())

        usage = RequestUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=_cost((model, prompt_tokens, completion_tokens)),
        )

        result = CreateResponse(finish_reason=stop_reason, content=content, usage=usage, cached=False)

        if cache is not None:
            cache.set(cache_key, result)

        _add_usage(self._actual_usage, usage)
        _add_usage(self._total_usage, usage)

        # TODO - why is this cast needed?
        yield cast(CreateResponse, result)

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage
