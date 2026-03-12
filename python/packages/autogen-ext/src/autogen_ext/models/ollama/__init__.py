try:
    from ._ollama_client import OllamaChatCompletionClient
except ImportError as e:
    raise ImportError(
        "Dependencies for Ollama not found. " "Please install the ollama package: " "pip install autogen-ext[ollama]"
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
