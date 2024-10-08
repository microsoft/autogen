import asyncio

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import (
    AgentId,
    AgentInstantiationContext,
    AgentType,
    Subscription,
    SubscriptionInstantiationContext,
    TopicId,
    try_get_known_serializers_for_type,
)
from autogen_core.components import (
    DefaultTopicId,
    TypeSubscription,
    type_subscription,
)
from opentelemetry.sdk.trace import TracerProvider
from test_utils import (
    CascadingAgent,
    CascadingMessageType,
    LoopbackAgent,
    LoopbackAgentWithDefaultSubscription,
    MessageType,
    NoopAgent,
)
from test_utils.telemetry_test_utils import TestExporter, get_test_tracer_provider

test_exporter = TestExporter()


@pytest.fixture
def tracer_provider() -> TracerProvider:
    test_exporter.clear()
    return get_test_tracer_provider(test_exporter)


@pytest.mark.asyncio
async def test_agent_type_must_be_unique() -> None:
    runtime = SingleThreadedAgentRuntime()

    def agent_factory() -> NoopAgent:
        id = AgentInstantiationContext.current_agent_id()
        assert id == AgentId("name1", "default")
        agent = NoopAgent()
        assert agent.id == id
        return agent

    await NoopAgent.register(runtime, "name1", agent_factory)

    # await runtime.register_factory(type=AgentType("name1"), agent_factory=agent_factory, expected_class=NoopAgent)

    with pytest.raises(ValueError):
        await runtime.register_factory(type=AgentType("name1"), agent_factory=agent_factory, expected_class=NoopAgent)

    await runtime.register_factory(type=AgentType("name2"), agent_factory=agent_factory, expected_class=NoopAgent)


@pytest.mark.asyncio
async def test_register_receives_publish(tracer_provider: TracerProvider) -> None:
    runtime = SingleThreadedAgentRuntime(tracer_provider=tracer_provider)

    runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await runtime.register_factory(
        type=AgentType("name"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
    )
    await runtime.add_subscription(TypeSubscription("default", "name"))

    runtime.start()
    await runtime.publish_message(MessageType(), topic_id=TopicId("default", "default"))
    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(AgentId("name", "default"), type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0

    exported_spans = test_exporter.get_exported_spans()
    assert len(exported_spans) == 3
    span_names = [span.name for span in exported_spans]
    assert span_names == [
        "autogen create default.(default)-T",
        "autogen process name.(default)-A",
        "autogen publish default.(default)-T",
    ]


@pytest.mark.asyncio
async def test_register_receives_publish_cascade() -> None:
    num_agents = 5
    num_initial_messages = 5
    max_rounds = 5
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    runtime = SingleThreadedAgentRuntime()

    # Register agents
    for i in range(num_agents):
        await CascadingAgent.register(runtime, f"name{i}", lambda: CascadingAgent(max_rounds))

    runtime.start()

    # Publish messages
    for _ in range(num_initial_messages):
        await runtime.publish_message(CascadingMessageType(round=1), DefaultTopicId())

    # Process until idle.
    await runtime.stop_when_idle()

    # Check that each agent received the correct number of messages.
    for i in range(num_agents):
        agent = await runtime.try_get_underlying_agent_instance(AgentId(f"name{i}", "default"), CascadingAgent)
        assert agent.num_calls == total_num_calls_expected


@pytest.mark.asyncio
async def test_register_factory_explicit_name() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name", LoopbackAgent, lambda: [TypeSubscription("default", "name")])
    runtime.start()
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_register_factory_context_var_name() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register(
        "name", LoopbackAgent, lambda: [TypeSubscription("default", SubscriptionInstantiationContext.agent_type().type)]
    )
    runtime.start()
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_register_factory_async() -> None:
    runtime = SingleThreadedAgentRuntime()

    async def sub_factory() -> list[Subscription]:
        await asyncio.sleep(0.1)
        return [TypeSubscription("default", SubscriptionInstantiationContext.agent_type().type)]

    await runtime.register("name", LoopbackAgent, sub_factory)
    runtime.start()
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_register_factory_direct_list() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name", LoopbackAgent, [TypeSubscription("default", "name")])
    runtime.start()
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_default_subscription() -> None:
    runtime = SingleThreadedAgentRuntime()
    runtime.start()

    await LoopbackAgentWithDefaultSubscription.register(runtime, "name", LoopbackAgentWithDefaultSubscription)

    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()

    long_running_agent = await runtime.try_get_underlying_agent_instance(
        agent_id, type=LoopbackAgentWithDefaultSubscription
    )
    assert long_running_agent.num_calls == 1

    other_long_running_agent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithDefaultSubscription
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_type_subscription() -> None:
    runtime = SingleThreadedAgentRuntime()
    runtime.start()

    @type_subscription(topic_type="Other")
    class LoopbackAgentWithSubscription(LoopbackAgent): ...

    await LoopbackAgentWithSubscription.register(runtime, "name", LoopbackAgentWithSubscription)

    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=TopicId("Other", "default"))
    await runtime.stop_when_idle()

    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgentWithSubscription)
    assert long_running_agent.num_calls == 1

    other_long_running_agent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithSubscription
    )
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_default_subscription_publish_to_other_source() -> None:
    runtime = SingleThreadedAgentRuntime()
    runtime.start()

    await LoopbackAgentWithDefaultSubscription.register(runtime, "name", LoopbackAgentWithDefaultSubscription)

    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(source="other"))
    await runtime.stop_when_idle()

    long_running_agent = await runtime.try_get_underlying_agent_instance(
        agent_id, type=LoopbackAgentWithDefaultSubscription
    )
    assert long_running_agent.num_calls == 0

    other_long_running_agent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithDefaultSubscription
    )
    assert other_long_running_agent.num_calls == 1
