
import inspect
from typing import Any, AsyncGenerator, Dict, List, Union, cast
from openai import AsyncOpenAI, AsyncAzureOpenAI
from typing_extensions import Self
from jsonschema import validate

from autogen._pydantic import type2schema
from autogen.cache.cache import Cache
from autogen.model_client.base import TextModelClient
from .types import ChatMessage, CreateResponse, RequestUsage, ToolCall
from autogen.oai.openai_utils import OAI_PRICE1K, get_key

openai_init_kwargs = set(inspect.getfullargspec(AsyncOpenAI.__init__).kwonlyargs)
aopenai_init_kwargs = set(inspect.getfullargspec(AsyncAzureOpenAI.__init__).kwonlyargs)

create_kwargs = set(inspect.getfullargspec(AsyncOpenAI.chat.completions.create).kwonlyargs)
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

from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam, ChatCompletionMessageParam
from openai.types.chat import ChatCompletion
oai_system_message_schema = type2schema(ChatCompletionSystemMessageParam)
oai_user_message_schema = type2schema(ChatCompletionUserMessageParam)
oai_assistant_message_schema = type2schema(ChatCompletionAssistantMessageParam)
oai_tool_message_schema = type2schema(ChatCompletionToolMessageParam)

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

def _cost(response: ChatCompletion) -> float:
    """Calculate the cost of the response."""
    model = response.model
    if model not in OAI_PRICE1K:
        # TODO: add logging to warn that the model is not found
        # logger.debug(f"Model {model} is not found. The cost will be 0.", exc_info=True)
        return 0

    n_input_tokens = response.usage.prompt_tokens if response.usage is not None else 0
    n_output_tokens = response.usage.completion_tokens if response.usage is not None else 0
    tmp_price1K = OAI_PRICE1K[model]
    # First value is input token rate, second value is output token rate
    if isinstance(tmp_price1K, tuple):
        return (tmp_price1K[0] * n_input_tokens + tmp_price1K[1] * n_output_tokens) / 1000
    return tmp_price1K * (n_input_tokens + n_output_tokens) / 1000

class OpenAITextModelClient(TextModelClient):
    def __init__(self, client: Union[AsyncOpenAI, AsyncAzureOpenAI], create_args: Dict[str, Any]) -> None:
        self._client = client
        self._create_args = create_args

    @classmethod
    def create_from_config(cls, config: Dict[str, str]) -> Self:
        client = _openai_client_from_config(config)
        create_args = _create_args_from_config(config)
        return cls(client, create_args)

    async def create(self, messages: List[ChatMessage], cache: Cache, extra_create_args: Dict[str, Any]) -> CreateResponse:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        cache_key = get_key({**create_args,"messages": messages})
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cast(CreateResponse, cached_value)

        oai_messages = [to_oai_type(m) for m in messages]

        # TODO: incorporate cache

        result = await self._client.chat.completions.create(messages=oai_messages, stream=False, **create_args)

        usage = RequestUsage(
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
            total_tokens=result.usage.total_tokens,
            cost=_cost(result),
            model=result.model,
        )

        # Limited to a single choice currently.
        choice = result.choices[0]
        content: Union[str, List[ToolCall]]
        if choice.finish_reason == "tool_calls":
            assert choice.message.tool_calls is not None
            assert choice.message.function_call is None

            # NOTE: If OAI response type changes, this will need to be updated
            tool_calls = [
                x.model_dump() for x in choice.message.tool_calls
            ]
            content = tool_calls
        else:
            content = choice.message.content or ""


        result = CreateResponse(
                finish_reason=choice.finish_reason,
                content=content,
                usage=usage
            )

        cache.set(cache_key, result)

        # TODO - why is this cast needed?
        return cast(CreateResponse, result)

    def create_stream(self, messages: List[ChatMessage], cache: Cache, extra_create_args: Dict[str, Any]) -> AsyncGenerator[Union[str, ToolCall, CreateResponse], None]:
        raise NotImplementedError