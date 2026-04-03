try:
    from ._sk_chat_completion_adapter import SKChatCompletionAdapter
except ImportError as e:
    raise ImportError(
        f"Dependencies for Semantic Kernel model client not found: {e}\n"
        'Please install autogen-ext with the "semantic-kernel-core" extra: '
        'pip install "autogen-ext[semantic-kernel-core]"'
    ) from e

__all__ = ["SKChatCompletionAdapter"]
