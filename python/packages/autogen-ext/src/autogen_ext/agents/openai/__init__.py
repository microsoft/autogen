try:
    from ._openai_assistant_agent import OpenAIAssistantAgent
except ImportError as e:
    raise ImportError(
        "Dependencies for OpenAIAssistantAgent not found. "
        "Please install autogen-ext with the 'openai' extra: "
        "pip install 'autogen-ext[openai]'"
    ) from e

__all__ = ["OpenAIAssistantAgent"]
