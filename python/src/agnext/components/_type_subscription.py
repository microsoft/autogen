from agnext.core.exceptions import CantHandleException

from ..core import AgentId, Subscription, TopicId


class TypeSubscription(Subscription):
    def __init__(self, topic_type: str, agent_type: str):
        """This subscription matches on topics based on the type and maps to agents using the source of the topic as the agent key.

        This subscription causes each source to have its own agent instance.

        Example:

            .. code-block:: python

                subscription = TypeSubscription(topic_type="t1", agent_type="a1")

            In this case:

            - A topic_id with type `t1` and source `s1` will be handled by an agent of type `a1` with key `s1`
            - A topic_id with type `t1` and source `s2` will be handled by an agent of type `a1` with key `s2`.

        Args:
            topic_type (str): Topic type to match against
            agent_type (str): Agent type to handle this subscription
        """

        self._topic_type = topic_type
        self._agent_type = agent_type

    def is_match(self, topic_id: TopicId) -> bool:
        return topic_id.type == self._topic_type

    def map_to_agent(self, topic_id: TopicId) -> AgentId:
        if not self.is_match(topic_id):
            raise CantHandleException("TopicId does not match the subscription")

        # TODO: Update agentid to reflect agent type and key
        return AgentId(name=self._agent_type, namespace=topic_id.source)
