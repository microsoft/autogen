import pytest
from autogen_ext.models._utils.parse_r1_content import parse_r1_content


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
