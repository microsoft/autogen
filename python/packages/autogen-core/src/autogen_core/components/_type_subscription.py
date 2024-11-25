import uuid
from typing import TypeVar

from ..base import AgentId, BaseAgent, Subscription, TopicId
from ..base.exceptions import CantHandleException


class TypeSubscription(Subscription):
    """This subscription matches on topics based on the type and maps to agents using the source of the topic as the agent key.

    This subscription causes each source to have its own agent instance.

    Example:

        .. code-block:: python

            from autogen_core.components import TypeSubscription

            subscription = TypeSubscription(topic_type="t1", agent_type="a1")

        In this case:

        - A topic_id with type `t1` and source `s1` will be handled by an agent of type `a1` with key `s1`
        - A topic_id with type `t1` and source `s2` will be handled by an agent of type `a1` with key `s2`.

    Args:
        topic_type (str): Topic type to match against
        agent_type (str): Agent type to handle this subscription
    """

    def __init__(self, topic_type: str, agent_type: str):
        self._topic_type = topic_type
        self._agent_type = agent_type
        self._id = str(uuid.uuid4())

    @property
    def id(self) -> str:
        return self._id

    @property
    def topic_type(self) -> str:
        return self._topic_type

    @property
    def agent_type(self) -> str:
        return self._agent_type

    def is_match(self, topic_id: TopicId) -> bool:
        return topic_id.type == self._topic_type

    def map_to_agent(self, topic_id: TopicId) -> AgentId:
        if not self.is_match(topic_id):
            raise CantHandleException("TopicId does not match the subscription")

        return AgentId(type=self._agent_type, key=topic_id.source)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypeSubscription):
            return False

        return self.id == other.id or (self.agent_type == other.agent_type and self.topic_type == other.topic_type)


BaseAgentType = TypeVar("BaseAgentType", bound="BaseAgent")
