"""Model information for Avian-hosted models."""

from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Avian model name aliases to their canonical identifiers.
_MODEL_POINTERS: Dict[str, str] = {
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
    "kimi-k2.5": "moonshotai/kimi-k2.5",
    "glm-5": "z-ai/glm-5",
    "minimax-m2.5": "minimax/minimax-m2.5",
}

# Model information for each Avian model.
_MODEL_INFO: Dict[str, ModelInfo] = {
    "deepseek/deepseek-v3.2": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
        "multiple_system_messages": True,
    },
    "moonshotai/kimi-k2.5": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
        "multiple_system_messages": True,
    },
    "z-ai/glm-5": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
        "multiple_system_messages": True,
    },
    "minimax/minimax-m2.5": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
        "multiple_system_messages": True,
    },
}

# Token limits (context window) for each model.
_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "deepseek/deepseek-v3.2": 164_000,
    "moonshotai/kimi-k2.5": 131_000,
    "z-ai/glm-5": 131_000,
    "minimax/minimax-m2.5": 1_000_000,
}

# Default token limit for unknown models.
_DEFAULT_TOKEN_LIMIT = 128_000


def resolve_model(model: str) -> str | None:
    """Resolve a model alias to its canonical name.

    Returns the canonical model name if found, otherwise None.
    """
    if model in _MODEL_INFO:
        return model
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return None


def get_info(model: str) -> ModelInfo:
    """Get the model info for a given model name.

    Raises:
        KeyError: If the model is not recognized.
    """
    resolved = resolve_model(model)
    if resolved is not None and resolved in _MODEL_INFO:
        return _MODEL_INFO[resolved]
    raise KeyError(f"Unknown Avian model: {model}")


def get_token_limit(model: str) -> int:
    """Get the token limit for a given model name."""
    resolved = resolve_model(model)
    if resolved is not None and resolved in _MODEL_TOKEN_LIMITS:
        return _MODEL_TOKEN_LIMITS[resolved]
    return _DEFAULT_TOKEN_LIMIT
