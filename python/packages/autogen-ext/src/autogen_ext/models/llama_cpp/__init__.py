try:
    from ._llama_cpp_completion_client import LlamaCppChatCompletionClient
except ImportError as e:
    raise ImportError(
        f"Dependencies for Llama Cpp not found. Original error: {e}\n"
        "Please install llama-cpp-python: "
        "pip install autogen-ext[llama-cpp]"
    ) from e

__all__ = ["LlamaCppChatCompletionClient"]
