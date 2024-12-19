try:
    from ._magentic_one_coder_agent import MagenticOneCoderAgent
except ImportError as e:
    raise ImportError(
        "Dependencies for MagenticOneCoderAgent not found. "
        'Please install autogen-ext with the "magentic-one" extra: '
        'pip install "autogen-ext[magentic-one]"'
    ) from e

__all__ = ["MagenticOneCoderAgent"]
