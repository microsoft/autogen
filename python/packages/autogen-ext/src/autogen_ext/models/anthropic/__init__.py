try:
    from ._anthropic_client import (
        AnthropicBedrockChatCompletionClient,
        AnthropicChatCompletionClient,
        BaseAnthropicChatCompletionClient,
    )
except ImportError as e:
    raise ImportError(
        "Dependencies for Anthropic not found. "
        "Please install the anthropic package: "
        "pip install autogen-ext[anthropic]"
    ) from e

from .config import (
    AnthropicBedrockClientConfiguration,
    AnthropicBedrockClientConfigurationConfigModel,
    AnthropicClientConfiguration,
    AnthropicClientConfigurationConfigModel,
    BedrockInfo,
    CreateArgumentsConfigModel,
)

__all__ = [
    "AnthropicChatCompletionClient",
    "AnthropicBedrockChatCompletionClient",
    "BaseAnthropicChatCompletionClient",
    "AnthropicClientConfiguration",
    "AnthropicBedrockClientConfiguration",
    "AnthropicClientConfigurationConfigModel",
    "AnthropicBedrockClientConfigurationConfigModel",
    "CreateArgumentsConfigModel",
    "BedrockInfo",
]
