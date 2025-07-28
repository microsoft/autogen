try:
    from ._openai_agent import OpenAIAgent

    # Check OpenAI version to conditionally import OpenAIAssistantAgent
    try:
        from openai import __version__ as openai_version

        def _parse_openai_version(version_str: str) -> tuple[int, int, int]:
            """Parse a semantic version string into a tuple of integers."""
            try:
                parts = version_str.split(".")
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0  # Handle pre-release versions
                return (major, minor, patch)
            except (ValueError, IndexError):
                # If version parsing fails, assume it's a newer version
                return (999, 999, 999)

        _current_version = _parse_openai_version(openai_version)
        _target_version = (1, 83, 0)

        # Only import OpenAIAssistantAgent if OpenAI version is less than 1.83
        if _current_version < _target_version:
            from ._openai_assistant_agent import OpenAIAssistantAgent  # type: ignore[import]

            __all__ = ["OpenAIAssistantAgent", "OpenAIAgent"]
        else:
            __all__ = ["OpenAIAgent"]
    except ImportError:
        # If OpenAI is not available, skip OpenAIAssistantAgent import
        __all__ = ["OpenAIAgent"]

except ImportError as e:
    raise ImportError(
        "Dependencies for OpenAI agents not found. "
        'Please install autogen-ext with the "openai" extra: '
        'pip install "autogen-ext[openai]"'
    ) from e
