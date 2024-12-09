import os
from typing import Any, List, Optional, Union

from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    UserMessage,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from typing_extensions import Literal

from .types import (
    FunctionCallMessage,
    Message,
    MultiModalMessage,
    TextMessage,
)


def convert_content_message_to_assistant_message(
    message: Union[TextMessage, MultiModalMessage, FunctionCallMessage],
    handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error",
) -> Optional[AssistantMessage]:
    match message:
        case TextMessage() | FunctionCallMessage():
            return AssistantMessage(content=message.content, source=message.source)
        case MultiModalMessage():
            if handle_unrepresentable == "error":
                raise ValueError("Cannot represent multimodal message as AssistantMessage")
            elif handle_unrepresentable == "ignore":
                return None
            elif handle_unrepresentable == "try_slice":
                return AssistantMessage(
                    content="".join([x for x in message.content if isinstance(x, str)]),
                    source=message.source,
                )


def convert_content_message_to_user_message(
    message: Union[TextMessage, MultiModalMessage, FunctionCallMessage],
    handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error",
) -> Optional[UserMessage]:
    match message:
        case TextMessage() | MultiModalMessage():
            return UserMessage(content=message.content, source=message.source)
        case FunctionCallMessage():
            if handle_unrepresentable == "error":
                raise ValueError("Cannot represent multimodal message as UserMessage")
            elif handle_unrepresentable == "ignore":
                return None
            elif handle_unrepresentable == "try_slice":
                # TODO: what is a sliced function call?
                raise NotImplementedError("Sliced function calls not yet implemented")


def convert_tool_call_response_message(
    message: FunctionExecutionResultMessage,
    handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error",
) -> Optional[FunctionExecutionResultMessage]:
    match message:
        case FunctionExecutionResultMessage():
            return FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content=x.content, call_id=x.call_id) for x in message.content]
            )


def convert_messages_to_llm_messages(
    messages: List[Message],
    self_name: str,
    handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error",
) -> List[LLMMessage]:
    result: List[LLMMessage] = []
    for message in messages:
        match message:
            case (
                TextMessage(content=_, source=source)
                | MultiModalMessage(content=_, source=source)
                | FunctionCallMessage(content=_, source=source)
            ) if source == self_name:
                converted_message_1 = convert_content_message_to_assistant_message(message, handle_unrepresentable)
                if converted_message_1 is not None:
                    result.append(converted_message_1)
            case (
                TextMessage(content=_, source=source)
                | MultiModalMessage(content=_, source=source)
                | FunctionCallMessage(content=_, source=source)
            ) if source != self_name:
                converted_message_2 = convert_content_message_to_user_message(message, handle_unrepresentable)
                if converted_message_2 is not None:
                    result.append(converted_message_2)
            case FunctionExecutionResultMessage(content=_):
                converted_message_3 = convert_tool_call_response_message(message, handle_unrepresentable)
                if converted_message_3 is not None:
                    result.append(converted_message_3)
            case _:
                raise AssertionError("unreachable")

    return result


def get_chat_completion_client_from_envs(**kwargs: Any) -> ChatCompletionClient:
    # Check API type.
    api_type = os.getenv("OPENAI_API_TYPE", "openai")
    if api_type == "openai":
        # Check API key.
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is not set")
        kwargs["api_key"] = api_key
        return OpenAIChatCompletionClient(**kwargs)
    elif api_type == "azure":
        # Check Azure API key.
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if azure_api_key is not None:
            kwargs["api_key"] = azure_api_key
        else:
            # Try to use token from Azure CLI.
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            kwargs["azure_ad_token_provider"] = token_provider
        # Check Azure API endpoint.
        azure_api_endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT")
        if azure_api_endpoint is None:
            raise ValueError("AZURE_OPENAI_API_ENDPOINT is not set")
        kwargs["azure_endpoint"] = azure_api_endpoint
        # Get Azure API version.
        kwargs["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        # Set model capabilities.
        if "model_capabilities" not in kwargs or kwargs["model_capabilities"] is None:
            kwargs["model_capabilities"] = {
                "vision": True,
                "function_calling": True,
                "json_output": True,
            }
        return AzureOpenAIChatCompletionClient(**kwargs)  # type: ignore
    raise ValueError(f"Unknown API type: {api_type}")
