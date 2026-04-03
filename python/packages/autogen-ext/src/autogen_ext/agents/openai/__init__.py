try:
    from ._openai_agent import OpenAIAgent
    from ._openai_assistant_agent import OpenAIAssistantAgent
except ImportError as e:
    raise ImportError(
        f"Dependencies for OpenAI agents not found: {e}\n"
        'Please install autogen-ext with the "openai" extra: '
        'pip install "autogen-ext[openai]"'
    ) from e

__all__ = [
    "OpenAIAgent",
    "OpenAIAssistantAgent",
]
