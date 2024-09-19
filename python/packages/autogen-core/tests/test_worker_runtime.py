import asyncio
import logging

import pytest
from autogen_core.application import WorkerAgentRuntime, WorkerAgentRuntimeHost
from autogen_core.base import (
    AgentId,
    AgentType,
    TopicId,
    try_get_known_serializers_for_type,
)
from autogen_core.components import DefaultSubscription, DefaultTopicId, TypeSubscription
from test_utils import CascadingAgent, CascadingMessageType, LoopbackAgent, MessageType, NoopAgent


@pytest.mark.asyncio
async def test_agent_types_must_be_unique_single_worker() -> None:
    host_address = "localhost:50051"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = WorkerAgentRuntime(host_address=host_address)
    worker.start()

    await worker.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    with pytest.raises(ValueError):
        await worker.register_factory(
            type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
        )

    await worker.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    await worker.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_agent_types_must_be_unique_multiple_workers() -> None:
    host_address = "localhost:50059"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker1 = WorkerAgentRuntime(host_address=host_address)
    worker1.start()
    worker2 = WorkerAgentRuntime(host_address=host_address)
    worker2.start()

    await worker1.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    with pytest.raises(RuntimeError):
        await worker2.register_factory(
            type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
        )

    await worker2.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    await worker1.stop()
    await worker2.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    host_address = "localhost:50060"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker1 = WorkerAgentRuntime(host_address=host_address)
    worker1.start()
    worker1.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker1.register_factory(
        type=AgentType("name1"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
    )
    await worker1.add_subscription(TypeSubscription("default", "name1"))

    worker2 = WorkerAgentRuntime(host_address=host_address)
    worker2.start()
    worker2.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker2.register_factory(
        type=AgentType("name2"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
    )
    await worker2.add_subscription(TypeSubscription("default", "name2"))

    # Publish message from worker1
    await worker1.publish_message(MessageType(), topic_id=TopicId("default", "default"))

    # Let the agent run for a bit.
    await asyncio.sleep(2)

    # Agents in default topic source should have received the message.
    worker1_agent = await worker1.try_get_underlying_agent_instance(AgentId("name1", "default"), LoopbackAgent)
    assert worker1_agent.num_calls == 1
    worker2_agent = await worker2.try_get_underlying_agent_instance(AgentId("name2", "default"), LoopbackAgent)
    assert worker2_agent.num_calls == 1

    # Agents in other topic source should not have received the message.
    worker1_agent = await worker1.try_get_underlying_agent_instance(AgentId("name1", "other"), LoopbackAgent)
    assert worker1_agent.num_calls == 0
    worker2_agent = await worker2.try_get_underlying_agent_instance(AgentId("name2", "other"), LoopbackAgent)
    assert worker2_agent.num_calls == 0

    await worker1.stop()
    await worker2.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_register_receives_publish_cascade_single_worker() -> None:
    host_address = "localhost:50053"
    host = WorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = WorkerAgentRuntime(host_address=host_address)
    runtime.start()

    num_agents = 5
    num_initial_messages = 5
    max_rounds = 5
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    # Register agents
    for i in range(num_agents):
        await CascadingAgent.register(runtime, f"name{i}", lambda: CascadingAgent(max_rounds))

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
        runtime.start()
        await CascadingAgent.register(runtime, f"name{i}", lambda: CascadingAgent(max_rounds))
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
