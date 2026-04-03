try:
    from ._azure_ai_client import AzureAIChatCompletionClient
except ImportError as e:
    raise ImportError(
        f"Dependencies for Azure AI model client not found: {e}\n"
        'Please install autogen-ext with the "azure" extra: '
        'pip install "autogen-ext[azure]"'
    ) from e

from .config import AzureAIChatCompletionClientConfig

__all__ = ["AzureAIChatCompletionClient", "AzureAIChatCompletionClientConfig"]
