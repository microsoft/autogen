from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Model version mappings (aliases to actual model names)
_MODEL_POINTERS = {
    "gemini-1.5-pro": "gemini-1.5-pro",
    "gemini-1.5-pro-vision": "gemini-1.5-pro-vision",
    "gemini-1.5-flash": "gemini-1.5-flash",
    "gemini-1.5-flash-8b": "gemini-1.5-flash-8b",
    "gemini-2.0-flash": "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite": "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash-preview": "gemini-2.0-flash-preview-02-05",
    "gemini-2.0-flash-lite-preview": "gemini-2.0-flash-lite-preview-02-05",
}

# Model capabilities and information
_MODEL_INFO: Dict[str, ModelInfo] = {
    "gemini-1.5-pro": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_PRO,
    },
    "gemini-1.5-pro-vision": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_PRO,
    },
    "gemini-1.5-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_FLASH,
    },
    "gemini-1.5-flash-8b": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_FLASH,
    },
    "gemini-2.0-flash-001": {
        "vision": True,
        "function_calling": True,
        "json_output": False,
        "family": ModelFamily.GEMINI_2_0_FLASH,
    },
    "gemini-2.0-flash-lite-001": {
        "vision": True,
        "function_calling": True,
        "json_output": False,
        "family": ModelFamily.GEMINI_2_0_FLASH,
    },
    "gemini-2.0-flash-preview-02-05": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Assuming no JSON output for preview
        "family": ModelFamily.GEMINI_2_0_FLASH,
    },
    "gemini-2.0-flash-lite-preview-02-05": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Assuming no JSON output for preview
        "family": ModelFamily.GEMINI_2_0_FLASH,
    },
}

# Experimental models
_EXPERIMENTAL_MODELS = {
    "gemini-1.5-pro-exp",
    "gemini-1.5-flash-exp",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-lite-exp",
}

# Token limits for each model (based on latest documentation)
_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "gemini-1.5-pro": 1_048_576,  # 1M tokens
    "gemini-1.5-pro-vision": 1_048_576,  # 1M tokens
    "gemini-1.5-flash": 1_048_576,  # 1M tokens
    "gemini-1.5-flash-8b": 1_048_576,  # 1M tokens
    "gemini-2.0-flash-001": 1_048_576,  # 1M tokens
    "gemini-2.0-flash-lite-001": 1_048_576,  # 1M tokens
    "gemini-2.0-flash-preview-02-05": 1_048_576,  # 1M tokens
    "gemini-2.0-flash-lite-preview-02-05": 1_048_576,  # 1M tokens
}


def resolve_model(model: str) -> str:
    """Resolve model aliases to their actual versions."""
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return model


def get_info(model: str) -> ModelInfo:
    """Get model capabilities and information."""
    resolved_model = resolve_model(model)
    return _MODEL_INFO[resolved_model]


def get_token_limit(model: str) -> int:
    """Get the token limit for a model."""
    resolved_model = resolve_model(model)
    return _MODEL_TOKEN_LIMITS[resolved_model]


def is_experimental_model(model: str) -> bool:
    """Check if a model is experimental."""
    resolved_model = resolve_model(model)
    return resolved_model in _EXPERIMENTAL_MODELS or any(
        exp_model in resolved_model for exp_model in _EXPERIMENTAL_MODELS
    )
