try:
    from ._llama_cpp_completion_client import LlamaCppChatCompletionClient
except ImportError as e:
    raise ImportError(
        "Dependencies for Llama Cpp not found. "
        "Please install llama-cpp-python: "
        "pip install autogen-ext[llama-cpp]"
    ) from e

__all__ = ["LlamaCppChatCompletionClient"]
