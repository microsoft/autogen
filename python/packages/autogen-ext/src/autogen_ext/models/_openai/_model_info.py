from typing import Dict

from autogen_core.components.models import ModelCapabilities

# Based on: https://platform.openai.com/docs/models/continuous-model-upgrades
# This is a moving target, so correctness is checked by the model value returned by openai against expected values at runtime``
_MODEL_POINTERS = {
    "gpt-4o": "gpt-4o-2024-08-06",
    "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
    "gpt-4-turbo": "gpt-4-turbo-2024-04-09",
    "gpt-4-turbo-preview": "gpt-4-0125-preview",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
    "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
}

_MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
    "gpt-4o-2024-08-06": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4o-2024-05-13": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4o-mini-2024-07-18": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4-turbo-2024-04-09": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4-0125-preview": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4-1106-preview": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4-1106-vision-preview": {
        "vision": True,
        "function_calling": False,
        "json_output": False,
    },
    "gpt-4-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-4-32k-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-3.5-turbo-0125": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-3.5-turbo-1106": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-3.5-turbo-instruct": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-3.5-turbo-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
    "gpt-3.5-turbo-16k-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
}

_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "gpt-4o-2024-08-06": 128000,
    "gpt-4o-2024-05-13": 128000,
    "gpt-4o-mini-2024-07-18": 128000,
    "gpt-4-turbo-2024-04-09": 128000,
    "gpt-4-0125-preview": 128000,
    "gpt-4-1106-preview": 128000,
    "gpt-4-1106-vision-preview": 128000,
    "gpt-4-0613": 8192,
    "gpt-4-32k-0613": 32768,
    "gpt-3.5-turbo-0125": 16385,
    "gpt-3.5-turbo-1106": 16385,
    "gpt-3.5-turbo-instruct": 4096,
    "gpt-3.5-turbo-0613": 4096,
    "gpt-3.5-turbo-16k-0613": 16385,
}


def resolve_model(model: str) -> str:
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return model


def get_capabilties(model: str) -> ModelCapabilities:
    resolved_model = resolve_model(model)
    return _MODEL_CAPABILITIES[resolved_model]


def get_token_limit(model: str) -> int:
    resolved_model = resolve_model(model)
    return _MODEL_TOKEN_LIMITS[resolved_model]
