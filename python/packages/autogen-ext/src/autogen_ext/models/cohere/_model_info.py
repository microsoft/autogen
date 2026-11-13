"""Model information for Cohere models."""

from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Mapping of Cohere model names to their capabilities
# Based on: https://docs.cohere.com/docs/models
_MODEL_INFO: Dict[str, ModelInfo] = {
    # Command R7B models
    "command-r7b-12-2024": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    "command-r7b-arabic-02-2025": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    # Command R models
    "command-r-08-2024": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    # Command A models
    "command-a-03-2025": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    "command-a-reasoning-08-2025": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    "command-a-vision-07-2025": ModelInfo(
        vision=True,
        function_calling=False,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    "command-a-translate-08-2025": ModelInfo(
        vision=False,
        function_calling=False,
        json_output=False,
        family=ModelFamily.UNKNOWN,
        structured_output=False,
        multiple_system_messages=False,
    ),
    # Takane
    "takane-v2-32b": ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
    "takane-vision-prerelease-10-2025": ModelInfo(
        vision=True,
        function_calling=False,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    ),
}


def normalize_model_name(model: str) -> str:
    """Normalize model name to handle different naming conventions."""
    # Cohere models are already normalized
    return model


def get_model_info(model: str) -> ModelInfo:
    """Get ModelInfo for a given Cohere model.

    Args:
        model: The model name.

    Returns:
        ModelInfo object with the model's capabilities.
    """
    normalized_model = normalize_model_name(model)

    if normalized_model in _MODEL_INFO:
        return _MODEL_INFO[normalized_model]

    # Default to basic capabilities for unknown models
    return ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=True,
        multiple_system_messages=False,
    )
