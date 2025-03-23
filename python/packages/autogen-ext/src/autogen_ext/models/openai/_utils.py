import re


def assert_valid_name(name: str) -> str:
    """
    Ensure that configured names are valid, raises ValueError if not.

    For munging LLM responses use _normalize_name to ensure LLM specified names don't break the API.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
    if len(name) > 64:
        raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
    return name
