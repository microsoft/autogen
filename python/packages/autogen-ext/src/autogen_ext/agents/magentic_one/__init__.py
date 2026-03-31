try:
    from ._magentic_one_coder_agent import MagenticOneCoderAgent
except ImportError as e:
    raise ImportError(
        f"Dependencies for MagenticOneCoderAgent not found. Original error: {e}\n"
        'Please install autogen-ext with the "magentic-one" extra: '
        'pip install "autogen-ext[magentic-one]"'
    ) from e

__all__ = ["MagenticOneCoderAgent"]
