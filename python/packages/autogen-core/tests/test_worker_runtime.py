import asyncio
import logging

import pytest
from autogen_core.application import WorkerAgentRuntime, WorkerAgentRuntimeHost
from autogen_core.base import (
    AgentId,
    AgentInstantiationContext,
    TopicId,
    try_get_known_serializers_for_type,
)
from autogen_core.components import DefaultSubscription, DefaultTopicId, TypeSubscription
from test_utils import CascadingAgent, CascadingMessageType, LoopbackAgent, MessageType, NoopAgent


@pytest.mark.asyncio
async def test_agent_names_must_be_unique() -> None:
    host_address = "localhost:50051"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = WorkerAgentRuntime(host_address=host_address)
    worker.start()

    def agent_factory() -> NoopAgent:
        id = AgentInstantiationContext.current_agent_id()
        assert id == AgentId("name1", "default")
        agent = NoopAgent()
        assert agent.id == id
        return agent

    await worker.register("name1", agent_factory)

    with pytest.raises(ValueError):
        await worker.register("name1", NoopAgent)

    await worker.register("name3", NoopAgent)

    # Let the agent run for a bit.
    await asyncio.sleep(2)

    await worker.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    host_address = "localhost:50052"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = WorkerAgentRuntime(host_address=host_address)
    worker.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    worker.start()

    await worker.register("name", LoopbackAgent)
    await worker.add_subscription(TypeSubscription("default", "name"))
    agent_id = AgentId("name", key="default")
    topic_id = TopicId("default", "default")
    await worker.publish_message(MessageType(), topic_id=topic_id)

    # Let the agent run for a bit.
    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await worker.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await worker.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0

    await worker.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_register_receives_publish_cascade() -> None:
    host_address = "localhost:50053"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = WorkerAgentRuntime(host_address=host_address)
    runtime.add_message_serializer(try_get_known_serializers_for_type(CascadingMessageType))
    runtime.start()

    num_agents = 5
    num_initial_messages = 5
    max_rounds = 5
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    # Register agents
    for i in range(num_agents):
        await runtime.register(f"name{i}", lambda: CascadingAgent(max_rounds), lambda: [DefaultSubscription()])

    # Publish messages
    for _ in range(num_initial_messages):
        await runtime.publish_message(CascadingMessageType(round=1), topic_id=DefaultTopicId())

    # Wait for all agents to finish.
    await asyncio.sleep(10)

    # Check that each agent received the correct number of messages.
    for i in range(num_agents):
        agent = await runtime.try_get_underlying_agent_instance(AgentId(f"name{i}", "default"), CascadingAgent)
        assert agent.num_calls == total_num_calls_expected

    await runtime.stop()
    await host.stop()


@pytest.mark.skip(reason="Fix flakiness")
@pytest.mark.asyncio
async def test_register_receives_publish_cascade_multiple_workers() -> None:
    logging.basicConfig(level=logging.DEBUG)
    host_address = "localhost:50057"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    # TODO: Increasing num_initial_messages or max_round to 2 causes the test to fail.
    num_agents = 2
    num_initial_messages = 1
    max_rounds = 1
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    # Run multiple workers one for each agent.
    workers = []
    # Register agents
    for i in range(num_agents):
        runtime = WorkerAgentRuntime(host_address=host_address)
        runtime.add_message_serializer(try_get_known_serializers_for_type(CascadingMessageType))
        runtime.start()
        await runtime.register(f"name{i}", lambda: CascadingAgent(max_rounds), lambda: [DefaultSubscription()])
        workers.append(runtime)

    # Publish messages
    publisher = WorkerAgentRuntime(host_address=host_address)
    publisher.add_message_serializer(try_get_known_serializers_for_type(CascadingMessageType))
    publisher.start()
    for _ in range(num_initial_messages):
        await publisher.publish_message(CascadingMessageType(round=1), topic_id=DefaultTopicId())

    await asyncio.sleep(20)

    # Check that each agent received the correct number of messages.
    for i in range(num_agents):
        agent = await workers[i].try_get_underlying_agent_instance(AgentId(f"name{i}", "default"), CascadingAgent)
        assert agent.num_calls == total_num_calls_expected

    for worker in workers:
        await worker.stop()
    await publisher.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_default_subscription() -> None:
    host_address = "localhost:50054"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = WorkerAgentRuntime(host_address=host_address)
    runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    runtime.start()

    await runtime.register("name", LoopbackAgent, lambda: [DefaultSubscription()])
    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId())

    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0

    await runtime.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_non_default_default_subscription() -> None:
    host_address = "localhost:50055"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = WorkerAgentRuntime(host_address=host_address)
    runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    runtime.start()

    await runtime.register("name", LoopbackAgent, lambda: [DefaultSubscription(topic_type="Other")])
    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(type="Other"))

    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 0

    await runtime.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_non_publish_to_other_source() -> None:
    host_address = "localhost:50056"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = WorkerAgentRuntime(host_address=host_address)
    runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    runtime.start()

    await runtime.register("name", LoopbackAgent, lambda: [DefaultSubscription()])
    agent_id = AgentId("name", key="default")
    await runtime.publish_message(MessageType(), topic_id=DefaultTopicId(source="other"))

    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(agent_id, type=LoopbackAgent)
    assert long_running_agent.num_calls == 0

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgent
    )
    assert other_long_running_agent.num_calls == 1

    await runtime.stop()
    await host.stop()
