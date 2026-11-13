from autogen_core.models import ModelFamily
from autogen_ext.models.anthropic import _model_info


def test_claude_sonnet_4_6_model_info() -> None:
    info = _model_info.get_info("claude-sonnet-4-6")
    assert info["family"] == ModelFamily.CLAUDE_4_SONNET
    assert info["vision"] is True
    assert info["function_calling"] is True
    assert _model_info.get_token_limit("claude-sonnet-4-6") == 1000000
