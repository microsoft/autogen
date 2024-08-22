import asyncio
import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.components._type_subscription import TypeSubscription
from agnext.core import AgentId, AgentInstantiationContext
from agnext.core import TopicId
from agnext.core._subscription import Subscription
from agnext.core._subscription_context import SubscriptionInstantiationContext
from test_utils import CascadingAgent, CascadingMessageType, LoopbackAgent, MessageType, NoopAgent


@pytest.mark.asyncio
async def test_agent_names_must_be_unique() -> None:
    runtime = SingleThreadedAgentRuntime()

    def agent_factory() -> NoopAgent:
        id = AgentInstantiationContext.current_agent_id()
        assert id == AgentId("name1", "default")
        agent = NoopAgent()
        assert agent.id == id
        return agent

    await runtime.register("name1", agent_factory)

    with pytest.raises(ValueError):
        await runtime.register("name1", NoopAgent)

    await runtime.register("name3", NoopAgent)


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name", LoopbackAgent)
    runtime.start()
    await runtime.add_subscription(TypeSubscription("default", "name"))
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(AgentId("name", key="other"), type=LoopbackAgent)
    assert other_long_running_agent.num_calls == 0


@pytest.mark.asyncio
async def test_register_receives_publish_cascade() -> None:
    runtime = SingleThreadedAgentRuntime()
    num_agents = 5
    num_initial_messages = 5
    max_rounds = 5
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    # Register agents
    for i in range(num_agents):
        await runtime.register(f"name{i}", lambda: CascadingAgent(max_rounds))
        await runtime.add_subscription(TypeSubscription("default", f"name{i}"))

    runtime.start()

    # Publish messages
    topic_id = TopicId("default", "default")
    for _ in range(num_initial_messages):
        await runtime.publish_message(CascadingMessageType(round=1), topic_id)

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
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(AgentId("name", key="other"), type=LoopbackAgent)
    assert other_long_running_agent.num_calls == 0

@pytest.mark.asyncio
async def test_register_factory_context_var_name() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name", LoopbackAgent, lambda: [TypeSubscription("default", SubscriptionInstantiationContext.agent_type().type)])
    runtime.start()
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await runtime.publish_message(MessageType(), topic_id=topic_id)

    await runtime.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(AgentId("name", key="other"), type=LoopbackAgent)
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
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(AgentId("name", key="other"), type=LoopbackAgent)
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
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(AgentId("name", key="other"), type=LoopbackAgent)
    assert other_long_running_agent.num_calls == 0
