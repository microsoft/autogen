import asyncio
import re
import warnings
from asyncio import Task
from typing import Sequence, Optional, Mapping, Any, List, Unpack, Dict, cast
from inspect import getfullargspec
from azure.ai.inference.aio import ChatCompletionsClient
from azure.ai.inference.models import (
    ChatCompletions,
    CompletionsFinishReason,
    ChatCompletionsToolCall,
    ChatCompletionsToolDefinition,
    FunctionDefinition,
    ContentItem,
    TextContentItem,
    ImageContentItem,
    ImageUrl,
    ImageDetailLevel,
    StreamingChatCompletionsUpdate,
    SystemMessage as AzureSystemMessage,
    UserMessage as AzureUserMessage,
    AssistantMessage as AzureAssistantMessage,
    ToolMessage as AzureToolMessage,
    FunctionCall as AzureFunctionCall,
)
from azure.ai.inference.models import (
    ChatCompletionsResponseFormatJSON,
)
from typing_extensions import AsyncGenerator, Union

from autogen_core import CancellationToken
from autogen_core import FunctionCall, Image
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    CreateResult,
    ModelCapabilities,
    RequestUsage,
    UserMessage,
    SystemMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.models.azure.config import AzureAIChatCompletionClientConfig, GITHUB_MODELS_ENDPOINT

create_kwargs = set(getfullargspec(ChatCompletionsClient.complete).kwonlyargs)


def _is_github_model(endpoint: str) -> bool:
    return endpoint == GITHUB_MODELS_ENDPOINT


def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[ChatCompletionsToolDefinition]:
    result: List[ChatCompletionsToolDefinition] = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema.copy()
        else:
            assert isinstance(tool, dict)
            tool_schema = tool.copy()
        # tool_schema["parameters"] = {k:v for k,v in tool_schema["parameters"].items()}
        # azure_ai_schema = {k:v for k,v in tool_schema["parameters"].items()}

        for key, value in tool_schema["parameters"]["properties"].items():
            if "title" in value.keys():
                del value["title"]

        result.append(
            ChatCompletionsToolDefinition(
                function=FunctionDefinition(
                    name=tool_schema["name"],
                    description=(tool_schema["description"] if "description" in tool_schema else ""),
                    parameters=(tool_schema["parameters"]) if "parameters" in tool_schema else {},
                ),
            ),
        )
    return result


def _func_call_to_azure(message: FunctionCall) -> ChatCompletionsToolCall:
    return ChatCompletionsToolCall(
        id=message.id,
        function=AzureFunctionCall(arguments=message.arguments, name=message.name),
    )


def _system_message_to_azure(message: SystemMessage) -> AzureSystemMessage:
    return AzureSystemMessage(content=message.content)


def _user_message_to_azure(message: UserMessage) -> AzureUserMessage:
    assert_valid_name(message.source)
    if isinstance(message.content, str):
        return AzureUserMessage(content=message.content)
    else:
        parts: List[ContentItem] = []
        for part in message.content:
            if isinstance(part, str):
                parts.append(TextContentItem(text=part))
            elif isinstance(part, Image):
                # TODO: support url based images
                # TODO: support specifying details
                parts.append(ImageContentItem(image_url=ImageUrl(url=part.data_uri, detail=ImageDetailLevel.AUTO)))
            else:
                raise ValueError(f"Unknown content type: {message.content}")
        return AzureUserMessage(content=parts)


def _assistant_message_to_azure(message: AssistantMessage) -> AzureAssistantMessage:
    assert_valid_name(message.source)
    if isinstance(message.content, list):
        return AzureAssistantMessage(
            tool_calls=[_func_call_to_azure(x) for x in message.content],
        )
    else:
        return AzureAssistantMessage(content=message.content)


def _tool_message_to_azure(message: FunctionExecutionResultMessage) -> Sequence[AzureToolMessage]:
    return [AzureToolMessage(content=x.content, tool_call_id=x.call_id) for x in message.content]


def to_azure_message(message: LLMMessage):
    if isinstance(message, SystemMessage):
        return [_system_message_to_azure(message)]
    elif isinstance(message, UserMessage):
        return [_user_message_to_azure(message)]
    elif isinstance(message, AssistantMessage):
        return [_assistant_message_to_azure(message)]
    else:
        return _tool_message_to_azure(message)


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


class AzureAIChatCompletionClient(ChatCompletionClient):
    """
    Chat completion client for models hosted on Azure AI Foundry or GitHub Models.
    See `here <https://learn.microsoft.com/en-us/azure/ai-studio/reference/reference-model-inference-chat-completions>`_ for more info.

    Args:
        endpoint (str): The endpoint to use. **Required.**
        credentials (union, AzureKeyCredential, AsyncTokenCredential): The credentials to use. **Required**
        model_capabilities (ModelCapabilities): The capabilities of the model. **Required.**
        model (str): The name of the model. **Required if model is hosted on GitHub Models.**
        frequency_penalty: (optional,float)
        presence_penalty: (optional,float)
        temperature: (optional,float)
        top_p: (optional,float)
        max_tokens: (optional,int)
        response_format: (optional,ChatCompletionsResponseFormat)
        stop: (optional,List[str])
        tools: (optional,List[ChatCompletionsToolDefinition])
        tool_choice: (optional,Union[str, ChatCompletionsToolChoicePreset, ChatCompletionsNamedToolChoice]])
        seed: (optional,int)
        model_extras: (optional,Dict[str, Any])

    To use this client, you must install the `azure-ai-inference` extension:

        .. code-block:: bash

            pip install 'autogen-ext[azure-ai-inference]==0.4.0.dev11'

    The following code snippet shows how to use the client:

        .. code-block:: python

            from azure.core.credentials import AzureKeyCredential
            from autogen_ext.models.azure import AzureAIChatCompletionClient
            from autogen_core.models import UserMessage

            client = AzureAIChatCompletionClient(
                endpoint="endpoint",
                credential=AzureKeyCredential("api_key"),
                model_capabilities={
                    "json_output": False,
                    "function_calling": False,
                    "vision": False,
                },
            )

            result = await client.create([UserMessage(content="What is the capital of France?", source="user")])  # type: ignore
            print(result)

    """

    def __init__(self, **kwargs: Unpack[AzureAIChatCompletionClientConfig]):
        config = self._validate_config(kwargs)
        self._model_capabilities = config["model_capabilities"]
        self._client = self._create_client(config)
        self._create_args = self._prepare_create_args(config)

        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @staticmethod
    def _validate_config(config: Dict) -> AzureAIChatCompletionClientConfig:
        if "endpoint" not in config:
            raise ValueError("endpoint is required for AzureAIChatCompletionClient")
        if "credential" not in config:
            raise ValueError("credential is required for AzureAIChatCompletionClient")
        if "model_capabilities" not in config:
            raise ValueError("model_capabilities is required for AzureAIChatCompletionClient")
        if _is_github_model(config["endpoint"]) and "model" not in config:
            raise ValueError("model is required for when using a Github model with AzureAIChatCompletionClient")
        return config

    @staticmethod
    def _create_client(config: AzureAIChatCompletionClientConfig):
        return ChatCompletionsClient(**config)

    @staticmethod
    def _prepare_create_args(config: Mapping[str, Any]) -> Mapping[str, Any]:
        create_args = {k: v for k, v in config.items() if k in create_kwargs}
        return create_args
        # self._endpoint = config.pop("endpoint")
        # self._credential = config.pop("credential")
        # self._model_capabilities = config.pop("model_capabilities")
        # self._create_args = config.copy()

    def add_usage(self, usage: RequestUsage):
        self._total_usage = RequestUsage(
            self._total_usage.prompt_tokens + usage.prompt_tokens,
            self._total_usage.completion_tokens + usage.completion_tokens,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        if self.capabilities["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True and "response_format" not in create_args:
                create_args["response_format"] = ChatCompletionsResponseFormatJSON()

        if self.capabilities["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output")
        if self.capabilities["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        azure_messages_nested = [to_azure_message(msg) for msg in messages]
        azure_messages = [item for sublist in azure_messages_nested for item in sublist]

        task: Task[ChatCompletions]

        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            task = asyncio.create_task(
                self._client.complete(messages=azure_messages, tools=converted_tools, **create_args)
            )
        else:
            task = asyncio.create_task(
                self._client.complete(
                    messages=azure_messages,
                    **create_args,
                )
            )

        if cancellation_token is not None:
            cancellation_token.link_future(task)

        result: ChatCompletions = await task

        usage = RequestUsage(
            prompt_tokens=result.usage.prompt_tokens if result.usage else 0,
            completion_tokens=result.usage.completion_tokens if result.usage else 0,
        )

        choice = result.choices[0]
        if choice.finish_reason == CompletionsFinishReason.TOOL_CALLS:
            assert choice.message.tool_calls is not None

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
            finish_reason = choice.finish_reason.value
            content = choice.message.content or ""

        response = CreateResult(
            finish_reason=finish_reason,  # type: ignore
            content=content,
            usage=usage,
            cached=False,
        )

        self.add_usage(usage)

        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        if self.capabilities["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.capabilities["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True and "response_format" not in create_args:
                create_args["response_format"] = ChatCompletionsResponseFormatJSON()

        if self.capabilities["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output")
        if self.capabilities["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        # azure_messages = [to_azure_message(m) for m in messages]
        azure_messages_nested = [to_azure_message(msg) for msg in messages]
        azure_messages = [item for sublist in azure_messages_nested for item in sublist]

        # task: Task[StreamingChatCompletionsUpdate]

        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            task = asyncio.create_task(
                self._client.complete(messages=azure_messages, tools=converted_tools, stream=True, **create_args)
            )
        else:
            task = asyncio.create_task(
                self._client.complete(messages=azure_messages, max_tokens=20, stream=True, **create_args)
            )

        if cancellation_token is not None:
            cancellation_token.link_future(task)

        # result: ChatCompletions = await task
        finish_reason = None
        content_deltas: List[str] = []
        full_tool_calls: Dict[str, FunctionCall] = {}
        prompt_tokens = 0
        completion_tokens = 0
        chunk: Optional[StreamingChatCompletionsUpdate] = None
        async for chunk in await task:
            choice = chunk.choices[0] if len(chunk.choices) > 0 else cast(StreamingChatCompletionsUpdate, None)
            if choice.finish_reason is not None:
                finish_reason = choice.finish_reason.value

            # We first try to load the content
            if choice.delta.content is not None:
                content_deltas.append(choice.delta.content)
                yield choice.delta.content
            # Otherwise, we try to load the tool calls
            if choice.delta.tool_calls is not None:
                for tool_call_chunk in choice.delta.tool_calls:
                    # print(tool_call_chunk)
                    if "index" in tool_call_chunk:
                        idx = tool_call_chunk["index"]
                    else:
                        idx = tool_call_chunk.id
                    if idx not in full_tool_calls:
                        full_tool_calls[idx] = FunctionCall(id="", arguments="", name="")

                    if tool_call_chunk.id is not None:
                        full_tool_calls[idx].id += tool_call_chunk.id

                    if tool_call_chunk.function is not None:
                        if tool_call_chunk.function.name is not None:
                            full_tool_calls[idx].name += tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments is not None:
                            full_tool_calls[idx].arguments += tool_call_chunk.function.arguments

        if chunk and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens

        if finish_reason is None:
            raise ValueError("No stop reason found")

        if choice and choice.finish_reason is CompletionsFinishReason.TOOL_CALLS:
            finish_reason = "function_calls"

        content: Union[str, List[FunctionCall]]

        if len(content_deltas) > 1:
            content = "".join(content_deltas)
            if chunk and chunk.usage:
                completion_tokens = chunk.usage.completion_tokens
            else:
                completion_tokens = 0
        else:
            content = list(full_tool_calls.values())

        usage = RequestUsage(
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
        )

        result = CreateResult(
            finish_reason=finish_reason,  # type: ignore
            content=content,
            usage=usage,
            cached=False,
        )

        self.add_usage(usage)

        yield result

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 0

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._model_capabilities

    def __del__(self):
        # TODO: This is a hack to close the open client
        try:
            asyncio.get_running_loop().create_task(self._client.close())
        except RuntimeError:
            asyncio.run(self._client.close())
