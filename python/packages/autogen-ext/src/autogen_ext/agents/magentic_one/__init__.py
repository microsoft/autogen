try:
    from ._magentic_one_coder_agent import MagenticOneCoderAgent
    from .magentic_one_computer_terminal_agent import MagenticOneComputerTerminalAgent
except ImportError as e:
    raise ImportError(
        "Dependencies for MagenticOne agents not found. "
        'Please install autogen-ext with the "magentic-one" extra: '
        'pip install "autogen-ext[magentic-one]"'
    ) from e

__all__ = ["MagenticOneCoderAgent", "MagenticOneComputerTerminalAgent"]
