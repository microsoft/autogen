import uuid

from ._agent_id import AgentId
from ._agent_type import AgentType
from ._subscription import Subscription
from ._topic import TopicId
from .exceptions import CantHandleException


class TypePrefixSubscription(Subscription):
    """This subscription matches on topics based on a prefix of the type and maps to agents using the source of the topic as the agent key.

    This subscription causes each source to have its own agent instance.

    Example:

        .. code-block:: python

            from autogen_core import TypePrefixSubscription

            subscription = TypePrefixSubscription(topic_type_prefix="t1", agent_type="a1")

        In this case:

        - A topic_id with type `t1` and source `s1` will be handled by an agent of type `a1` with key `s1`
        - A topic_id with type `t1` and source `s2` will be handled by an agent of type `a1` with key `s2`.
        - A topic_id with type `t1SUFFIX` and source `s2` will be handled by an agent of type `a1` with key `s2`.

    Args:
        topic_type_prefix (str): Topic type prefix to match against
        agent_type (str): Agent type to handle this subscription
    """

    def __init__(self, topic_type_prefix: str, agent_type: str | AgentType):
        self._topic_type_prefix = topic_type_prefix
        if isinstance(agent_type, AgentType):
            self._agent_type = agent_type.type
        else:
            self._agent_type = agent_type
        self._id = str(uuid.uuid4())

    @property
    def id(self) -> str:
        return self._id

    @property
    def topic_type_prefix(self) -> str:
        return self._topic_type_prefix

    @property
    def agent_type(self) -> str:
        return self._agent_type

    def is_match(self, topic_id: TopicId) -> bool:
        return topic_id.type.startswith(self._topic_type_prefix)

    def map_to_agent(self, topic_id: TopicId) -> AgentId:
        if not self.is_match(topic_id):
            raise CantHandleException("TopicId does not match the subscription")

        return AgentId(type=self._agent_type, key=topic_id.source)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypePrefixSubscription):
            return False

        return self.id == other.id or (
            self.agent_type == other.agent_type and self.topic_type_prefix == other.topic_type_prefix
        )
