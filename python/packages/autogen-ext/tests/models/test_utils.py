import pytest
from autogen_core.models import ModelFamily
from autogen_ext.models._utils.parse_r1_content import parse_r1_content
from autogen_ext.models.openai._model_info import (
    MISTRAL_API_BASE_URL,
    get_info,
    resolve_model,
)


def test_parse_r1_content() -> None:
    content = "Hello, <think>world</think> How are you?"
    thought, content = parse_r1_content(content)
    assert thought == "world"
    assert content == "How are you?"

    with pytest.warns(
        UserWarning,
        match="Could not find <think>..</think> field in model response content. " "No thought was extracted.",
    ):
        content = "Hello, world How are you?"
        thought, content = parse_r1_content(content)
        assert thought is None
        assert content == "Hello, world How are you?"

    with pytest.warns(
        UserWarning,
        match="Could not find <think>..</think> field in model response content. " "No thought was extracted.",
    ):
        content = "Hello, <think>world How are you?"
        thought, content = parse_r1_content(content)
        assert thought is None
        assert content == "Hello, <think>world How are you?"

    with pytest.warns(
        UserWarning, match="Found </think> before <think> in model response content. " "No thought was extracted."
    ):
        content = "</think>Hello, <think>world</think>"
        thought, content = parse_r1_content(content)
        assert thought is None
        assert content == "</think>Hello, <think>world</think>"

    with pytest.warns(
        UserWarning, match="Found </think> before <think> in model response content. " "No thought was extracted."
    ):
        content = "</think>Hello, <think>world"
        thought, content = parse_r1_content(content)
        assert thought is None
        assert content == "</think>Hello, <think>world"


def test_mistral_model_info() -> None:
    assert resolve_model("mistral-large-latest") == "mistral-large-2411"
    assert resolve_model("codestral-latest") == "codestral-2501"
    assert resolve_model("pixtral-large-latest") == "pixtral-large-2411"

    info = get_info("mistral-large-latest")
    assert info["family"] == ModelFamily.MISTRAL
    assert info["function_calling"] is True
    assert info["json_output"] is True
    assert info["structured_output"] is True
    assert info["multiple_system_messages"] is False

    assert get_info("pixtral-large-latest")["vision"] is True
    assert get_info("open-codestral-mamba")["function_calling"] is False

    assert MISTRAL_API_BASE_URL == "https://api.mistral.ai/v1/"
