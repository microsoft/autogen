try:
    from ._llama_cpp_completion_client import LlamaCppChatCompletionClient
except ImportError as e:
    raise ImportError(
        f"Dependencies for Llama.cpp model client not found: {e}\n"
        'Please install autogen-ext with the "llama-cpp" extra: '
        'pip install "autogen-ext[llama-cpp]"'
    ) from e

__all__ = ["LlamaCppChatCompletionClient"]
