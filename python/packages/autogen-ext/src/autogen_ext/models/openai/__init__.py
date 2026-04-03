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
        f"Dependencies for OpenAI model client not found: {e}\n"
        'Please install autogen-ext with the "openai" extra: '
        'pip install "autogen-ext[openai]"'
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
