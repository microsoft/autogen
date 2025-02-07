import asyncio
import re
from asyncio import Task
from inspect import getfullargspec
from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

from autogen_core import CancellationToken, FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from azure.ai.inference.aio import ChatCompletionsClient
from azure.ai.inference.models import (
    AssistantMessage as AzureAssistantMessage,
)
from azure.ai.inference.models import (
    ChatCompletions,
    ChatCompletionsToolCall,
    ChatCompletionsToolDefinition,
    CompletionsFinishReason,
    ContentItem,
    FunctionDefinition,
    ImageContentItem,
    ImageDetailLevel,
    ImageUrl,
    StreamingChatChoiceUpdate,
    StreamingChatCompletionsUpdate,
    TextContentItem,
)
from azure.ai.inference.models import (
    FunctionCall as AzureFunctionCall,
)
from azure.ai.inference.models import (
    SystemMessage as AzureSystemMessage,
)
from azure.ai.inference.models import (
    ToolMessage as AzureToolMessage,
)
from azure.ai.inference.models import (
    UserMessage as AzureUserMessage,
)
from typing_extensions import AsyncGenerator, Union, Unpack

from autogen_ext.models.azure.config import (
    GITHUB_MODELS_ENDPOINT,
    AzureAIChatCompletionClientConfig,
)

from .._utils.parse_r1_content import parse_r1_content

create_kwargs = set(getfullargspec(ChatCompletionsClient.complete).kwonlyargs)
AzureMessage = Union[AzureSystemMessage, AzureUserMessage, AzureAssistantMessage, AzureToolMessage]


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

        if "parameters" in tool_schema:
            for value in tool_schema["parameters"]["properties"].values():
                if "title" in value.keys():
                    del value["title"]

        function_def: Dict[str, Any] = dict(name=tool_schema["name"])
        if "description" in tool_schema:
            function_def["description"] = tool_schema["description"]
        if "parameters" in tool_schema:
            function_def["parameters"] = tool_schema["parameters"]

        result.append(
            ChatCompletionsToolDefinition(
                function=FunctionDefinition(**function_def),
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


def to_azure_message(message: LLMMessage) -> Sequence[AzureMessage]:
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
        credential (union, AzureKeyCredential, AsyncTokenCredential): The credentials to use. **Required**
        model_info (ModelInfo): The model family and capabilities of the model. **Required.**
        model (str): The name of the model. **Required if model is hosted on GitHub Models.**
        frequency_penalty: (optional,float)
        presence_penalty: (optional,float)
        temperature: (optional,float)
        top_p: (optional,float)
        max_tokens: (optional,int)
        response_format: (optional, literal["text", "json_object"])
        stop: (optional,List[str])
        tools: (optional,List[ChatCompletionsToolDefinition])
        tool_choice: (optional,Union[str, ChatCompletionsToolChoicePreset, ChatCompletionsNamedToolChoice]])
        seed: (optional,int)
        model_extras: (optional,Dict[str, Any])

    To use this client, you must install the `azure-ai-inference` extension:

        .. code-block:: bash

            pip install "autogen-ext[azure]"

    The following code snippet shows how to use the client:

        .. code-block:: python

            import asyncio
            from azure.core.credentials import AzureKeyCredential
            from autogen_ext.models.azure import AzureAIChatCompletionClient
            from autogen_core.models import UserMessage


            async def main():
                client = AzureAIChatCompletionClient(
                    endpoint="endpoint",
                    credential=AzureKeyCredential("api_key"),
                    model_info={
                        "json_output": False,
                        "function_calling": False,
                        "vision": False,
                        "family": "unknown",
                    },
                )

                result = await client.create([UserMessage(content="What is the capital of France?", source="user")])
                print(result)


            if __name__ == "__main__":
                asyncio.run(main())

    """

    def __init__(self, **kwargs: Unpack[AzureAIChatCompletionClientConfig]):
        config = self._validate_config(kwargs)  # type: ignore
        self._model_info = config["model_info"]  # type: ignore
        self._client = self._create_client(config)
        self._create_args = self._prepare_create_args(config)

        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> AzureAIChatCompletionClientConfig:
        if "endpoint" not in config:
            raise ValueError("endpoint is required for AzureAIChatCompletionClient")
        if "credential" not in config:
            raise ValueError("credential is required for AzureAIChatCompletionClient")
        if "model_info" not in config:
            raise ValueError("model_info is required for AzureAIChatCompletionClient")
        if _is_github_model(config["endpoint"]) and "model" not in config:
            raise ValueError("model is required for when using a Github model with AzureAIChatCompletionClient")
        return cast(AzureAIChatCompletionClientConfig, config)

    @staticmethod
    def _create_client(config: AzureAIChatCompletionClientConfig) -> ChatCompletionsClient:
        return ChatCompletionsClient(**config)

    @staticmethod
    def _prepare_create_args(config: Mapping[str, Any]) -> Dict[str, Any]:
        create_args = {k: v for k, v in config.items() if k in create_kwargs}
        return create_args

    def add_usage(self, usage: RequestUsage) -> None:
        self._total_usage = RequestUsage(
            self._total_usage.prompt_tokens + usage.prompt_tokens,
            self._total_usage.completion_tokens + usage.completion_tokens,
        )

    def _validate_model_info(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema],
        json_output: Optional[bool],
        create_args: Dict[str, Any],
    ) -> None:
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if self.model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output")

            if json_output is True and "response_format" not in create_args:
                create_args["response_format"] = "json_object"

        if self.model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output")
        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
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

        self._validate_model_info(messages, tools, json_output, create_args)

        azure_messages_nested = [to_azure_message(msg) for msg in messages]
        azure_messages = [item for sublist in azure_messages_nested for item in sublist]

        task: Task[ChatCompletions]

        if len(tools) > 0:
            converted_tools = convert_tools(tools)
            task = asyncio.create_task(  # type: ignore
                self._client.complete(messages=azure_messages, tools=converted_tools, **create_args)  # type: ignore
            )
        else:
            task = asyncio.create_task(  # type: ignore
                self._client.complete(  # type: ignore
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

            content: Union[str, List[FunctionCall]] = [
                FunctionCall(
                    id=x.id,
                    arguments=x.function.arguments,
                    name=normalize_name(x.function.name),
                )
                for x in choice.message.tool_calls
            ]
            finish_reason = "function_calls"
        else:
            if isinstance(choice.finish_reason, CompletionsFinishReason):
                finish_reason = choice.finish_reason.value
            else:
                finish_reason = choice.finish_reason  # type: ignore
            content = choice.message.content or ""

        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1:
            thought, content = parse_r1_content(content)
        else:
            thought = None

        response = CreateResult(
            finish_reason=finish_reason,  # type: ignore
            content=content,
            usage=usage,
            cached=False,
            thought=thought,
        )

        self.add_usage(usage)

        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        create_args: Dict[str, Any] = self._create_args.copy()
        create_args.update(extra_create_args)

        self._validate_model_info(messages, tools, json_output, create_args)

        # azure_messages = [to_azure_message(m) for m in messages]
        azure_messages_nested = [to_azure_message(msg) for msg in messages]
        azure_messages = [item for sublist in azure_messages_nested for item in sublist]

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
        finish_reason: Optional[FinishReasons] = None
        content_deltas: List[str] = []
        full_tool_calls: Dict[str, FunctionCall] = {}
        prompt_tokens = 0
        completion_tokens = 0
        chunk: Optional[StreamingChatCompletionsUpdate] = None
        choice: Optional[StreamingChatChoiceUpdate] = None
        async for chunk in await task:  # type: ignore
            assert isinstance(chunk, StreamingChatCompletionsUpdate)
            choice = chunk.choices[0] if len(chunk.choices) > 0 else None
            if choice and choice.finish_reason is not None:
                if isinstance(choice.finish_reason, CompletionsFinishReason):
                    finish_reason = cast(FinishReasons, choice.finish_reason.value)
                else:
                    if choice.finish_reason in ["stop", "length", "function_calls", "content_filter", "unknown"]:
                        finish_reason = choice.finish_reason  # type: ignore
                    else:
                        raise ValueError(f"Unexpected finish reason: {choice.finish_reason}")

            # We first try to load the content
            if choice and choice.delta.content is not None:
                content_deltas.append(choice.delta.content)
                yield choice.delta.content
            # Otherwise, we try to load the tool calls
            if choice and choice.delta.tool_calls is not None:
                for tool_call_chunk in choice.delta.tool_calls:
                    # print(tool_call_chunk)
                    if "index" in tool_call_chunk:
                        idx = tool_call_chunk["index"]
                    else:
                        idx = tool_call_chunk.id
                    if idx not in full_tool_calls:
                        full_tool_calls[idx] = FunctionCall(id="", arguments="", name="")

                    full_tool_calls[idx].id += tool_call_chunk.id
                    full_tool_calls[idx].name += tool_call_chunk.function.name
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

        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1:
            thought, content = parse_r1_content(content)
        else:
            thought = None

        result = CreateResult(
            finish_reason=finish_reason,
            content=content,
            usage=usage,
            cached=False,
            thought=thought,
        )

        self.add_usage(usage)

        yield result

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 0

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info

    def __del__(self) -> None:
        # TODO: This is a hack to close the open client
        try:
            asyncio.get_running_loop().create_task(self._client.close())
        except RuntimeError:
            asyncio.run(self._client.close())
