try:
    from ._ollama_client import OllamaChatCompletionClient
except ImportError as e:
    raise ImportError(
        f"Dependencies for Ollama model client not found: {e}\n"
        'Please install autogen-ext with the "ollama" extra: '
        'pip install "autogen-ext[ollama]"'
    ) from e

from .config import (
    BaseOllamaClientConfigurationConfigModel,
    CreateArgumentsConfigModel,
)

__all__ = [
    "OllamaChatCompletionClient",
    "BaseOllamaClientConfigurationConfigModel",
    "CreateArgumentsConfigModel",
]
