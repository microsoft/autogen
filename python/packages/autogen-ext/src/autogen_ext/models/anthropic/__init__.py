from .config import (
    AnthropicBedrockClientConfiguration,
    AnthropicBedrockClientConfigurationConfigModel,
    AnthropicClientConfiguration,
    AnthropicClientConfigurationConfigModel,
    BedrockInfo,
    CreateArgumentsConfigModel,
)

try:
    from ._anthropic_client import (
        AnthropicBedrockChatCompletionClient,
        AnthropicChatCompletionClient,
        BaseAnthropicChatCompletionClient,
    )
except ImportError as e:  # pragma: no cover - only triggered when optional deps are missing
    raise ImportError(
        "Failed to import Anthropic dependencies required for AnthropicChatCompletionClient "
        "and AnthropicBedrockChatCompletionClient.\n"
        f"Original error: {e}\n"
        "Required packages (installed via the 'anthropic' extra):\n"
        '  pip install "autogen-ext[anthropic]"'
    ) from e

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
