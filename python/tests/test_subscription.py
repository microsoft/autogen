from agnext.components import TypeSubscription
from agnext.base import TopicId, AgentId

import pytest

from agnext.base.exceptions import CantHandleException

def test_type_subscription_match() -> None:
    sub = TypeSubscription(topic_type="t1", agent_type="a1")

    assert sub.is_match(TopicId(type="t0", source="s1")) == False
    assert sub.is_match(TopicId(type="t1", source="s1")) == True
    assert sub.is_match(TopicId(type="t1", source="s2")) == True


def test_type_subscription_map() -> None:
    sub = TypeSubscription(topic_type="t1", agent_type="a1")

    assert sub.map_to_agent(TopicId(type="t1", source="s1")) == AgentId(type="a1", key="s1")

    with pytest.raises(CantHandleException):
        _agent_id = sub.map_to_agent(TopicId(type="t0", source="s1"))
