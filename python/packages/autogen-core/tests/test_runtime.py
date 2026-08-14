import logging

import pytest
from autogen_core import (
    AgentId,
    AgentInstantiationContext,
    AgentType,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    event,
    try_get_known_serializers_for_type,
    type_subscription,
)
from autogen_core._default_subscription import default_subscription
from autogen_test_utils import (
    CascadingAgent,
    CascadingMessageType,
    LoopbackAgent,
    LoopbackAgentWithDefaultSubscription,
    MessageType,
    NoopAgent,
)
from autogen_test_utils.telemetry_test_utils import MyTestExporter, get_test_tracer_provider
from opentelemetry.sdk.trace import TracerProvider

test_exporter = MyTestExporter()


@pytest.fixture
def tracer_provider() -> TracerProvider:
    test_exporter.clear()
    return get_test_tracer_provider(test_exporter)


@pytest.mark.asyncio
async def test_agent_type_register_factory() -> None:
    runtime = SingleThreadedAgentRuntime()

    def agent_factory() -> NoopAgent:
        id = AgentInstantiationContext.current_agent_id()
        assert id == AgentId("name1", "default")
        agent = NoopAgent()
        assert agent.id == id
        return agent

    await runtime.register_factory(type=AgentType("name1"), agent_factory=agent_factory, expected_class=NoopAgent)

    with pytest.raises(ValueError):
        # This should fail because the expected class does not match the actual class.
        await runtime.register_factory(
            type=AgentType("name1"),
            agent_factory=agent_factory,  # type: ignore
            expected_class=CascadingAgent,
        )

    # Without expected_class, no error.
    await runtime.register_factory(type=AgentType("name2"), agent_factory=agent_factory)


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
async def test_agent_type_register_instance() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent1_id = AgentId(type="name", key="default")
    agent2_id = AgentId(type="name", key="notdefault")
    agent1 = NoopAgent()
    agent1_dup = NoopAgent()
    agent2 = NoopAgent()
    await agent1.register_instance(runtime=runtime, agent_id=agent1_id)
    await agent2.register_instance(runtime=runtime, agent_id=agent2_id)

    assert await runtime.try_get_underlying_agent_instance(agent1_id, type=NoopAgent) == agent1
    assert await runtime.try_get_underlying_agent_instance(agent2_id, type=NoopAgent) == agent2
    with pytest.raises(ValueError):
        await agent1_dup.register_instance(runtime=runtime, agent_id=agent1_id)


@pytest.mark.asyncio
async def test_agent_type_register_instance_different_types() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent_id1 = AgentId(type="name", key="noop")
    agent_id2 = AgentId(type="name", key="loopback")
    agent1 = NoopAgent()
    agent2 = LoopbackAgent()
    await agent1.register_instance(runtime=runtime, agent_id=agent_id1)
    with pytest.raises(ValueError):
        await agent2.register_instance(runtime=runtime, agent_id=agent_id2)


@pytest.mark.asyncio
async def test_agent_type_register_instance_publish_new_source() -> None:
    runtime = SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)
    agent_id = AgentId(type="name", key="default")
    agent1 = LoopbackAgent()
    await agent1.register_instance(runtime=runtime, agent_id=agent_id)
    await runtime.add_subscription(TypeSubscription("notdefault", "name"))

    runtime.start()
    with pytest.raises(RuntimeError):
        await runtime.publish_message(MessageType(), TopicId("notdefault", "notdefault"))
        await runtime.stop_when_idle()
    await runtime.close()


@pytest.mark.asyncio
async def test_register_instance_factory() -> None:
    runtime = SingleThreadedAgentRuntime()
    agent1_id = AgentId(type="name", key="default")
    agent1 = NoopAgent()
    await agent1.register_instance(runtime=runtime, agent_id=agent1_id)
    with pytest.raises(ValueError):
        await NoopAgent.register(runtime, "name", lambda: NoopAgent())


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

    await runtime.close()


@pytest.mark.asyncio
async def test_register_receives_publish_with_construction(caplog: pytest.LogCaptureFixture) -> None:
    runtime = SingleThreadedAgentRuntime()

    runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))

    async def agent_factory() -> LoopbackAgent:
        raise ValueError("test")

    await runtime.register_factory(type=AgentType("name"), agent_factory=agent_factory, expected_class=LoopbackAgent)
    await runtime.add_subscription(TypeSubscription("default", "name"))

    with caplog.at_level(logging.ERROR):
        runtime.start()
        await runtime.publish_message(MessageType(), topic_id=TopicId("default", "default"))
        await runtime.stop_when_idle()

    # Check if logger has the exception.
    assert any("Error constructing agent" in e.message for e in caplog.records)

    await runtime.close()


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

    await runtime.close()


@pytest.mark.asyncio
async def test_register_factory_explicit_name() -> None:
    runtime = SingleThreadedAgentRuntime()

    await LoopbackAgent.register(runtime, "name", LoopbackAgent)
    await runtime.add_subscription(TypeSubscription("default", "name"))

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

    await runtime.close()


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

    await runtime.close()


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

    await runtime.close()


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

    await runtime.close()


@default_subscription
class FailingAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A failing agent.")

    @event
    async def on_new_message_event(self, message: MessageType, ctx: MessageContext) -> None:
        raise ValueError("Test exception")


@pytest.mark.asyncio
async def test_event_handler_exception_propogates() -> None:
    runtime = SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)
    await FailingAgent.register(runtime, "name", FailingAgent)

    with pytest.raises(ValueError, match="Test exception"):
        runtime.start()
        await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
        await runtime.stop_when_idle()

    await runtime.close()


@pytest.mark.asyncio
async def test_event_handler_exception_multi_message() -> None:
    runtime = SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)
    await FailingAgent.register(runtime, "name", FailingAgent)

    with pytest.raises(ValueError, match="Test exception"):
        runtime.start()
        await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
        await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
        await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())
        await runtime.stop_when_idle()

    await runtime.close()
