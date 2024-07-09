import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from agnext.components.models import (
    AzureOpenAIChatCompletionClient,
    ChatCompletionClient,
    ModelCapabilities,
    OpenAIChatCompletionClient,
)

from .messages import OrchestrationEvent

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
        _kwargs["model_capabilities"] = ModelCapabilities(
            vision=_kwargs["model_capabilities"].get("vision"),
            function_calling=_kwargs["model_capabilities"].get("function_calling"),
            json_output=_kwargs["model_capabilities"].get("json_output"),
        )

    # Figure out what provider we are using. Default to OpenAI
    _provider = env.get(ENVIRON_KEY_CHAT_COMPLETION_PROVIDER, "openai").lower().strip()

    # Instantiate the correct client
    if _provider == "openai":
        return OpenAIChatCompletionClient(**_kwargs)
    elif _provider == "azure":
        if _kwargs.get("azure_ad_token_provider", "").lower() == "default":
            if _default_azure_ad_token_provider is None:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                _default_azure_ad_token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
            _kwargs["azure_ad_token_provider"] = _default_azure_ad_token_provider
        return AzureOpenAIChatCompletionClient(**_kwargs)
    else:
        raise ValueError(f"Unknown OAI provider '{_provider}'")


# TeamOne log event handler
class LogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, OrchestrationEvent):
                ts = datetime.fromtimestamp(record.created).isoformat()
                print(
                    f"""
---------------------------------------------------------------------------
\033[91m[{ts}], {record.msg.source}:\033[0m

{record.msg.message}""",
                    flush=True,
                )
        except Exception:
            self.handleError(record)
