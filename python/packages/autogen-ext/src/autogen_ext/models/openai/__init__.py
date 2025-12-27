from . import _message_transform

try:
    from ._openai_client import (
        AZURE_OPENAI_USER_AGENT,
        AzureOpenAIChatCompletionClient,
        BaseOpenAIChatCompletionClient,
        OpenAIChatCompletionClient,
    )
except ImportError as e:
    raise ImportError(
        "Dependencies for OpenAI not found. " "Please install the openai package: " "pip install autogen-ext[openai]"
    ) from e

from .config import (
    AzureOpenAIClientConfigurationConfigModel,
    BaseOpenAIClientConfigurationConfigModel,
    CreateArgumentsConfigModel,
    OpenAIClientConfigurationConfigModel,
)

__all__ = [
    "OpenAIChatCompletionClient",
    "AzureOpenAIChatCompletionClient",
    "BaseOpenAIChatCompletionClient",
    "AzureOpenAIClientConfigurationConfigModel",
    "OpenAIClientConfigurationConfigModel",
    "BaseOpenAIClientConfigurationConfigModel",
    "CreateArgumentsConfigModel",
    "AZURE_OPENAI_USER_AGENT",
    "_message_transform",
]
