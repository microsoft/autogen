import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, TopicId
from autogen_core.base.exceptions import CantHandleException
from autogen_core.components import DefaultSubscription, DefaultTopicId, TypeSubscription
from test_utils import LoopbackAgent, MessageType


def test_type_subscription_match() -> None:
    sub = TypeSubscription(topic_type="t1", agent_type="a1")

    assert sub.is_match(TopicId(type="t0", source="s1")) is False
    assert sub.is_match(TopicId(type="t1", source="s1")) is True
    assert sub.is_match(TopicId(type="t1", source="s2")) is True


def test_type_subscription_map() -> None:
    sub = TypeSubscription(topic_type="t1", agent_type="a1")

    assert sub.map_to_agent(TopicId(type="t1", source="s1")) == AgentId(type="a1", key="s1")

    with pytest.raises(CantHandleException):
        _agent_id = sub.map_to_agent(TopicId(type="t0", source="s1"))


@pytest.mark.asyncio
async def test_non_default_default_subscription() -> None:
    runtime = SingleThreadedAgentRuntime()

    await LoopbackAgent.register(runtime, "MyAgent", LoopbackAgent, skip_class_subscriptions=True)
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    # Not subscribed
    agent_instance = await runtime.try_get_underlying_agent_instance(
        AgentId("MyAgent", key="default"), type=LoopbackAgent
    )
    assert agent_instance.num_calls == 0

    # Subscribed
    default_subscription = TypeSubscription("default", "MyAgent")
    await runtime.add_subscription(default_subscription)

    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    assert agent_instance.num_calls == 1

    # Publish to a different unsubscribed topic
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(type="other"))
    await runtime.stop_when_idle()

    assert agent_instance.num_calls == 1

    # Add a subscription to the other topic
    await runtime.add_subscription(TypeSubscription("other", "MyAgent"))

    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(type="other"))
    await runtime.stop_when_idle()

    assert agent_instance.num_calls == 2

    # Remove the subscription
    await runtime.remove_subscription(default_subscription.id)

    # Publish to the default topic
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    assert agent_instance.num_calls == 2

    # Publish to the other topic
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(type="other"))
    await runtime.stop_when_idle()

    assert agent_instance.num_calls == 3


@pytest.mark.asyncio
async def test_skipped_class_subscriptions() -> None:
    runtime = SingleThreadedAgentRuntime()

    await LoopbackAgent.register(runtime, "MyAgent", LoopbackAgent, skip_class_subscriptions=True)
    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    # Not subscribed
    agent_instance = await runtime.try_get_underlying_agent_instance(
        AgentId("MyAgent", key="default"), type=LoopbackAgent
    )
    assert agent_instance.num_calls == 0


@pytest.mark.asyncio
async def test_subscription_deduplication() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent_type = "MyAgent"

    # Test TypeSubscription
    type_subscription_1 = TypeSubscription("default", agent_type)
    type_subscription_2 = TypeSubscription("default", agent_type)

    await runtime.add_subscription(type_subscription_1)
    with pytest.raises(ValueError, match="Subscription already exists"):
        await runtime.add_subscription(type_subscription_2)

    # Test DefaultSubscription
    default_subscription = DefaultSubscription(agent_type=agent_type)
    with pytest.raises(ValueError, match="Subscription already exists"):
        await runtime.add_subscription(default_subscription)
