import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Literal

from autogen_core import Image
from autogen_core.logging import LLMCallEvent
from autogen_core.models import (
    ChatCompletionClient,
    ModelCapabilities,  # type: ignore
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient

from .messages import (
    AgentEvent,
    AssistantContent,
    FunctionExecutionContent,
    OrchestrationEvent,
    SystemContent,
    UserContent,
    WebSurferEvent,
)

ENVIRON_KEY_CHAT_COMPLETION_PROVIDER = "CHAT_COMPLETION_PROVIDER"
ENVIRON_KEY_CHAT_COMPLETION_KWARGS_JSON = "CHAT_COMPLETION_KWARGS_JSON"

# The singleton _default_azure_ad_token_provider, which will be created if needed
_default_azure_ad_token_provider = None


# Create a model client based on information provided in environment variables.
def create_completion_client_from_env(env: Dict[str, str] | None = None, **kwargs: Any) -> ChatCompletionClient:
    global _default_azure_ad_token_provider

    """
    Create a model client based on information provided in environment variables.
        env (Optional):     When provied, read from this dictionary rather than os.environ
        kwargs**:           ChatClient arguments to override (e.g., model)

    NOTE: If 'azure_ad_token_provider' is included, and euquals the string 'DEFAULT' then replace it with
          azure.identity.get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    """

    # If a dictionary was not provided, load it from the environment
    if env is None:
        env = dict()
        env.update(os.environ)

    # Load the kwargs, and override with provided kwargs
    _kwargs = json.loads(env.get(ENVIRON_KEY_CHAT_COMPLETION_KWARGS_JSON, "{}"))
    _kwargs.update(kwargs)

    # If model capabilities were provided, deserialize them as well
    if "model_capabilities" in _kwargs:
        _kwargs["model_capabilities"] = ModelCapabilities(  # type: ignore
            vision=_kwargs["model_capabilities"].get("vision"),
            function_calling=_kwargs["model_capabilities"].get("function_calling"),
            json_output=_kwargs["model_capabilities"].get("json_output"),
        )

    # Figure out what provider we are using. Default to OpenAI
    _provider = env.get(ENVIRON_KEY_CHAT_COMPLETION_PROVIDER, "openai").lower().strip()

    # Instantiate the correct client
    if _provider == "openai":
        return OpenAIChatCompletionClient(**_kwargs)  # type: ignore
    elif _provider == "azure":
        if _kwargs.get("azure_ad_token_provider", "").lower() == "default":
            if _default_azure_ad_token_provider is None:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                _default_azure_ad_token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
            _kwargs["azure_ad_token_provider"] = _default_azure_ad_token_provider
        return AzureOpenAIChatCompletionClient(**_kwargs)  # type: ignore
    else:
        raise ValueError(f"Unknown OAI provider '{_provider}'")


# Convert UserContent to a string
def message_content_to_str(
    message_content: UserContent | AssistantContent | SystemContent | FunctionExecutionContent,
) -> str:
    if isinstance(message_content, str):
        return message_content
    elif isinstance(message_content, List):
        converted: List[str] = list()
        for item in message_content:
            if isinstance(item, str):
                converted.append(item.rstrip())
            elif isinstance(item, Image):
                converted.append("<Image>")
            else:
                converted.append(str(item).rstrip())
        return "\n".join(converted)
    else:
        raise AssertionError("Unexpected response type.")


# MagenticOne log event handler
class LogHandler(logging.FileHandler):
    def __init__(self, filename: str = "log.jsonl") -> None:
        super().__init__(filename)
        self.logs_list: List[Dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).isoformat()
            if isinstance(record.msg, OrchestrationEvent):
                console_message = (
                    f"\n{'-'*75} \n" f"\033[91m[{ts}], {record.msg.source}:\033[0m\n" f"\n{record.msg.message}"
                )
                print(console_message, flush=True)
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "source": record.msg.source,
                        "message": record.msg.message,
                        "type": "OrchestrationEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, AgentEvent):
                console_message = (
                    f"\n{'-'*75} \n" f"\033[91m[{ts}], {record.msg.source}:\033[0m\n" f"\n{record.msg.message}"
                )
                print(console_message, flush=True)
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "source": record.msg.source,
                        "message": record.msg.message,
                        "type": "AgentEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, WebSurferEvent):
                console_message = f"\033[96m[{ts}], {record.msg.source}: {record.msg.message}\033[0m"
                print(console_message, flush=True)
                payload: Dict[str, Any] = {
                    "timestamp": ts,
                    "type": "WebSurferEvent",
                }
                payload.update(asdict(record.msg))
                record.msg = json.dumps(payload)
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, LLMCallEvent):
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "prompt_tokens": record.msg.prompt_tokens,
                        "completion_tokens": record.msg.completion_tokens,
                        "type": "LLMCallEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
        except Exception:
            self.handleError(record)


class SentinelMeta(type):
    """
    A baseclass for sentinels that plays well with type hints.
    Define new sentinels like this:

    ```
    class MY_DEFAULT(metaclass=SentinelMeta):
        pass


    foo: list[str] | None | type[MY_DEFAULT] = MY_DEFAULT
    ```

    Reference: https://stackoverflow.com/questions/69239403/type-hinting-parameters-with-a-sentinel-value-as-the-default
    """

    def __repr__(cls) -> str:
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        return False
