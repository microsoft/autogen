try:
    from ._azure_ai_client import AzureAIChatCompletionClient
    from .config import AzureAIChatCompletionClientConfig
except ImportError as e:  # pragma: no cover - only triggered when optional deps are missing
    raise ImportError(
        "Failed to import Azure AI dependencies required for AzureAIChatCompletionClient.\n"
        f"Original error: {e}\n"
        "Required packages (installed via the 'azure' extra):\n"
        '  pip install "autogen-ext[azure]"'
    ) from e

__all__ = ["AzureAIChatCompletionClient", "AzureAIChatCompletionClientConfig"]
