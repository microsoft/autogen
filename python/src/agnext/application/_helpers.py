from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, List, Set

from ..core._agent import Agent
from ..core._agent_id import AgentId
from ..core._agent_type import AgentType
from ..core._subscription import Subscription
from ..core._topic import TopicId


async def get_impl(
    *,
    id_or_type: AgentId | AgentType | str,
    key: str,
    lazy: bool,
    instance_getter: Callable[[AgentId], Awaitable[Agent]],
) -> AgentId:
    if isinstance(id_or_type, AgentId):
        if not lazy:
            await instance_getter(id_or_type)

        return id_or_type

    type_str = id_or_type if isinstance(id_or_type, str) else id_or_type.type
    id = AgentId(type_str, key)
    if not lazy:
        await instance_getter(id)

    return id


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscriptions: List[Subscription] = []
        self._seen_topics: Set[TopicId] = set()
        self._subscribed_recipients: DefaultDict[TopicId, List[AgentId]] = defaultdict(list)

    async def add_subscription(self, subscription: Subscription) -> None:
        # Check if the subscription already exists
        if any(sub.id == subscription.id for sub in self._subscriptions):
            raise ValueError("Subscription already exists")

        if len(self._seen_topics) > 0:
            raise NotImplementedError("Cannot add subscription after topics have been seen yet")

        self._subscriptions.append(subscription)

    async def remove_subscription(self, id: str) -> None:
        # Check if the subscription exists
        if not any(sub.id == id for sub in self._subscriptions):
            raise ValueError("Subscription does not exist")

        def is_not_sub(x: Subscription) -> bool:
            return x.id != id

        self._subscriptions = list(filter(is_not_sub, self._subscriptions))

        # Rebuild the subscriptions
        self._rebuild_subscriptions(self._seen_topics)

    async def get_subscribed_recipients(self, topic: TopicId) -> List[AgentId]:
        if topic not in self._seen_topics:
            self._build_for_new_topic(topic)
        return self._subscribed_recipients[topic]

    # TODO: optimize this...
    def _rebuild_subscriptions(self, topics: Set[TopicId]) -> None:
        self._subscribed_recipients.clear()
        for topic in topics:
            self._build_for_new_topic(topic)

    def _build_for_new_topic(self, topic: TopicId) -> None:
        if topic in self._seen_topics:
            return

        self._seen_topics.add(topic)
        for subscription in self._subscriptions:
            if subscription.is_match(topic):
                self._subscribed_recipients[topic].append(subscription.map_to_agent(topic))
