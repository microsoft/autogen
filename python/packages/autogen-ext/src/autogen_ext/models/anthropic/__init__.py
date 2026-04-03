try:
    from ._anthropic_client import (
        AnthropicBedrockChatCompletionClient,
        AnthropicChatCompletionClient,
        BaseAnthropicChatCompletionClient,
    )
except ImportError as e:
    raise ImportError(
        f"Dependencies for Anthropic model client not found: {e}\n"
        'Please install autogen-ext with the "anthropic" extra: '
        'pip install "autogen-ext[anthropic]"'
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
