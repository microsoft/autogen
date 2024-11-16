from typing import Dict

from autogen_core.components.models import ModelCapabilities


# https://ai.google.dev/gemini-api/docs/models/gemini

_MODEL_POINTERS = {
    "gemini-pro": "gemini-1.0-pro",
}

_MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
    "gemini-1.5-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gemini-1.5-flash-8b": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gemini-1.5-pro": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gemini-1.0-pro": {
        "vision": False,
        "function_calling": True,
        "json_output": False,
    },
}

_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "gemini-1.0-pro": 24_568,
    "gemini-1.5-flash": 1_048_576,
    "gemini-1.5-flash-8b": 1_048_576,
    "gemini-1.5-pro": 2_097_152,
}


def resolve_model(model: str) -> str:
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return model


def get_capabilities(model: str) -> ModelCapabilities:
    resolved_model = resolve_model(model)
    return _MODEL_CAPABILITIES[resolved_model]


def get_token_limit(model: str) -> int:
    resolved_model = resolve_model(model)
    return _MODEL_TOKEN_LIMITS[resolved_model]
