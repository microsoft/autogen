from autogen_core.models import ModelFamily, ModelInfo

_GEMINI_MODEL_INFO = {
    "gemini-1.5-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_FLASH,
    },
    "gemini-1.5-pro": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_PRO,
    },
    "gemini-2.0-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_2_0_FLASH,
    },
}


def get_info(model_name: str) -> ModelInfo:
    """Return a ModelInfo for the given Gemini model name, or a default fallback if unknown."""
    if model_name in _GEMINI_MODEL_INFO:
        return _GEMINI_MODEL_INFO[model_name]
    return {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.UNKNOWN,
    }


_GEMINI_TOKEN_LIMITS = {
    "gemini-1.5-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-1.5-pro": 2097152,
}


def get_token_limit(model_name: str) -> int:
    return _GEMINI_TOKEN_LIMITS.get(model_name)
