import pytest

from autogen_core._topic import TopicId


def test_a_topic_type_that_is_not_a_string_is_named():
    with pytest.raises(ValueError, match="Invalid topic type"):
        TopicId(type=123, source="src")


def test_a_topic_type_that_breaks_the_pattern_is_named():
    with pytest.raises(ValueError, match="Invalid topic type"):
        TopicId(type="has space", source="src")


def test_valid_topic_ids_still_work():
    topic_id = TopicId(type="agents.info", source="host:42")

    assert str(topic_id) == "agents.info/host:42"
    assert TopicId.from_str("agents.info/host:42") == topic_id
