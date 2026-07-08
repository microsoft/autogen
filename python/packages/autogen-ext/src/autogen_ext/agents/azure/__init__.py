try:
    from ._azure_ai_agent import AzureAIAgent
except ImportError as e:
    raise ImportError(
        "Dependencies for AzureAIAgent not found. "
        'Please install autogen-ext with the "azure" extra: '
        'pip install "autogen-ext[azure]"'
    ) from e

__all__ = ["AzureAIAgent"]
