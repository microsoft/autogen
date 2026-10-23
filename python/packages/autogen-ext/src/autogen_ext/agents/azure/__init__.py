try:
    from ._azure_ai_agent import AzureAIAgent
except ImportError as e:
    raise ImportError(
        f"Dependencies for AzureAIAgent not found. Original error: {e}\n"
        'Please install autogen-ext with the "azure" extra: '
        'pip install "autogen-ext[azure]"'
    ) from e

__all__ = ["AzureAIAgent"]
