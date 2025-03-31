from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Based on: https://platform.openai.com/docs/models/continuous-model-upgrades
# This is a moving target, so correctness is checked by the model value returned by openai against expected values at runtime``
_MODEL_POINTERS = {
    "o3-mini": "o3-mini-2025-01-31",
    "o1": "o1-2024-12-17",
    "o1-preview": "o1-preview-2024-09-12",
    "o1-mini": "o1-mini-2024-09-12",
    "gpt-4.5-preview": "gpt-4.5-preview-2025-02-27",
    "gpt-4o": "gpt-4o-2024-08-06",
    "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
    "gpt-4-turbo": "gpt-4-turbo-2024-04-09",
    "gpt-4-turbo-preview": "gpt-4-0125-preview",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
    "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-7-sonnet": "claude-3-7-sonnet-20250219",
}

_MODEL_INFO: Dict[str, ModelInfo] = {
    "o3-mini-2025-01-31": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.O3,
        "structured_output": True,
    },
    "o1-2024-12-17": {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.O1,
        "structured_output": True,
    },
    "o1-preview-2024-09-12": {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.O1,
        "structured_output": True,
    },
    "o1-mini-2024-09-12": {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.O1,
        "structured_output": False,
    },
    "gpt-4.5-preview-2025-02-27": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_45,
        "structured_output": True,
    },
    "gpt-4o-2024-11-20": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4O,
        "structured_output": True,
    },
    "gpt-4o-2024-08-06": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4O,
        "structured_output": True,
    },
    "gpt-4o-2024-05-13": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4O,
        "structured_output": False,
    },
    "gpt-4o-mini-2024-07-18": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4O,
        "structured_output": True,
    },
    "gpt-4-turbo-2024-04-09": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-4-0125-preview": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-4-1106-preview": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-4-1106-vision-preview": {
        "vision": True,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-4-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-4-32k-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_4,
        "structured_output": False,
    },
    "gpt-3.5-turbo-0125": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_35,
        "structured_output": False,
    },
    "gpt-3.5-turbo-1106": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_35,
        "structured_output": False,
    },
    "gpt-3.5-turbo-instruct": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_35,
        "structured_output": False,
    },
    "gpt-3.5-turbo-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_35,
        "structured_output": False,
    },
    "gpt-3.5-turbo-16k-0613": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GPT_35,
        "structured_output": False,
    },
    "gemini-1.5-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_FLASH,
        "structured_output": True,
    },
    "gemini-1.5-flash-8b": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_FLASH,
        "structured_output": True,
    },
    "gemini-1.5-pro": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_1_5_PRO,
        "structured_output": True,
    },
    "gemini-2.0-flash": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_2_0_FLASH,
        "structured_output": True,
    },
    "gemini-2.0-flash-lite-preview-02-05": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.GEMINI_2_0_FLASH,
        "structured_output": True,
    },
    "claude-3-haiku-20240307": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_HAIKU,
        "structured_output": False,
    },
    "claude-3-sonnet-20240229": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_SONNET,
        "structured_output": False,
    },
    "claude-3-opus-20240229": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_OPUS,
        "structured_output": False,
    },
    "claude-3-5-haiku-20241022": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_5_HAIKU,
        "structured_output": False,
    },
    "claude-3-5-sonnet-20241022": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
    },
    "claude-3-7-sonnet-20250219": {
        "vision": True,
        "function_calling": True,
        "json_output": False,  # Update this when Anthropic supports structured output
        "family": ModelFamily.CLAUDE_3_7_SONNET,
        "structured_output": False,
    },
}

_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "o3-mini-2025-01-31": 200000,
    "o1-2024-12-17": 200000,
    "o1-preview-2024-09-12": 128000,
    "o1-mini-2024-09-12": 128000,
    "gpt-4.5-preview-2025-02-27": 128000,
    "gpt-4o-2024-11-20": 128000,
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
    "gemini-1.5-flash": 1048576,
    "gemini-1.5-flash-8b": 1048576,
    "gemini-1.5-pro": 2097152,
    "gemini-2.0-flash": 1048576,
    "gemini-2.0-flash-lite-preview-02-05": 1048576,
    "claude-3-haiku-20240307": 50000,
    "claude-3-sonnet-20240229": 40000,
    "claude-3-opus-20240229": 20000,
    "claude-3-5-haiku-20241022": 50000,
    "claude-3-5-sonnet-20241022": 40000,
    "claude-3-7-sonnet-20250219": 20000,
}

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
ANTHROPIC_OPENAI_BASE_URL = "https://api.anthropic.com/v1/"


def resolve_model(model: str) -> str:
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return model


def get_info(model: str) -> ModelInfo:
    resolved_model = resolve_model(model)
    return _MODEL_INFO[resolved_model]


def get_token_limit(model: str) -> int:
    resolved_model = resolve_model(model)
    return _MODEL_TOKEN_LIMITS[resolved_model]
