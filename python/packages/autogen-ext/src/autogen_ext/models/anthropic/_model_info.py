from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Bedrock provider/region prefixes that can appear before the model name
_BEDROCK_PREFIXES = (
    "us.anthropic.",
    "us-east-1.anthropic.",
    "us-west-2.anthropic.",
    "eu.anthropic.",
    "eu-west-1.anthropic.",
    "apac.anthropic.",
    "ap-southeast-1.anthropic.",
    "global.anthropic.",
    "anthropic.",
)


def _normalize_model_id(model: str) -> str:
    """Strip Bedrock provider/region prefixes and version suffixes to get the base model ID."""
    # Strip Bedrock prefixes
    for prefix in _BEDROCK_PREFIXES:
        if model.startswith(prefix):
            model = model[len(prefix) :]
            break
    # Strip version suffix like -v1:0, -v2:1
    if "-v" in model:
        model = model.split("-v")[0]
    return model


# Mapping of model names to their capabilities

# Mapping of model names to their capabilities
# For Anthropic's Claude models based on:
# https://docs.anthropic.com/claude/docs/models-overview
_MODEL_INFO: Dict[str, ModelInfo] = {
    # Claude 4 Opus
    "claude-opus-4-20250514": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_4_OPUS,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 4 Opus latest alias
    "claude-opus-4-0": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_4_OPUS,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 4 Sonnet
    "claude-sonnet-4-20250514": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_4_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 4 Sonnet latest alias
    "claude-sonnet-4-0": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_4_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3.7 Sonnet
    "claude-3-7-sonnet-20250219": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_7_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3.7 Sonnet latest alias
    "claude-3-7-sonnet-latest": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_7_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3 Opus (most powerful)
    "claude-3-opus-20240229": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3 Sonnet (balanced)
    "claude-3-sonnet-20240229": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3 Haiku (fastest)
    "claude-3-haiku-20240307": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20240620": {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude Instant v1 (legacy)
    "claude-instant-1.2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 2 (legacy)
    "claude-2.0": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
    # Claude 2.1 (legacy)
    "claude-2.1": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.CLAUDE_3_5_SONNET,
        "structured_output": False,
        "multiple_system_messages": False,
    },
}

# Model token limits (context window size)
_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "claude-3-opus-20240229": 200000,
    "claude-3-sonnet-20240229": 200000,
    "claude-3-haiku-20240307": 200000,
    "claude-3-5-sonnet-20240620": 200000,
    "claude-3-7-sonnet-20250219": 200000,
    "claude-instant-1.2": 100000,
    "claude-2.0": 100000,
    "claude-2.1": 200000,
}


def get_info(model: str) -> ModelInfo:
    """Get the model information for a specific model."""
    # Normalize Bedrock-style model IDs
    normalized = _normalize_model_id(model)

    # Check for exact match first
    if normalized in _MODEL_INFO:
        return _MODEL_INFO[normalized]

    # Check for partial match (for handling model variants)
    for model_id in _MODEL_INFO:
        if normalized.startswith(model_id.split("-2")[0]):  # Match base name
            return _MODEL_INFO[model_id]

    raise KeyError(f"Model '{model}' not found in model info")


def get_token_limit(model: str) -> int:
    """Get the token limit for a specific model."""
    # Normalize Bedrock-style model IDs
    normalized = _normalize_model_id(model)

    # Check for exact match first
    if normalized in _MODEL_TOKEN_LIMITS:
        return _MODEL_TOKEN_LIMITS[normalized]

    # Check for partial match (for handling model variants)
    for model_id in _MODEL_TOKEN_LIMITS:
        if normalized.startswith(model_id.split("-2")[0]):  # Match base name
            return _MODEL_TOKEN_LIMITS[model_id]

    # Default to a reasonable limit if model not found
    return 100000
