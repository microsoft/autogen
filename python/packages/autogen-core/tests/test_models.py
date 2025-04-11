import pytest
from autogen_core.models import ModelInfo, validate_model_info


def test_model_info() -> None:
    # Valid model info.
    info: ModelInfo = {
        "family": "gpt-4o",
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "structured_output": True,
    }
    validate_model_info(info)

    # Invalid model info.
    info = {
        "family": "gpt-4o",
        "vision": True,
        "function_calling": True,
    }  # type: ignore
    with pytest.raises(ValueError):
        validate_model_info(info)
