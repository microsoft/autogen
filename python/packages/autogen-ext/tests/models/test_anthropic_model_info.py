import pytest
from autogen_core.models import ModelFamily
from autogen_ext.models.anthropic import _model_info


@pytest.mark.parametrize(
    "model",
    [
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "global.anthropic.claude-3-5-sonnet-20240620-v1:0",
    ],
)
def test_bedrock_model_ids_resolve_model_info(model: str) -> None:
    info = _model_info.get_info(model)

    assert info["family"] == ModelFamily.CLAUDE_3_5_SONNET
    assert info == _model_info.get_info("claude-3-5-sonnet-20240620")


@pytest.mark.parametrize(
    "model",
    [
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    ],
)
def test_bedrock_model_ids_resolve_token_limit(model: str) -> None:
    assert _model_info.get_token_limit(model) == 200000

