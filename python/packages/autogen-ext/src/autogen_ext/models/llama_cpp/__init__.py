try:
    from ._llama_cpp_completion_client import LlamaCppChatCompletionClient
except ImportError as e:
    raise ImportError(
        "Dependencies for Llama Cpp not found. " "Please install llama-cpp-python: " "pip install llama-cpp-python"
    ) from e

__all__ = ["LlamaCppChatCompletionClient"]
