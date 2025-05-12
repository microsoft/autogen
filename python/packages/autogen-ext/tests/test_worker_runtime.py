import asyncio
import logging
import os
from typing import Any, List

import pytest
from autogen_core import (
    PROTOBUF_DATA_CONTENT_TYPE,
    AgentId,
    AgentType,
    DefaultSubscription,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    Subscription,
    TopicId,
    TypeSubscription,
    default_subscription,
    event,
    try_get_known_serializers_for_type,
    type_subscription,
)
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime, GrpcWorkerAgentRuntimeHost
from autogen_test_utils import (
    CascadingAgent,
    CascadingMessageType,
    ContentMessage,
    LoopbackAgent,
    LoopbackAgentWithDefaultSubscription,
    MessageType,
    NoopAgent,
)

from .protos.serialization_test_pb2 import ProtoMessage


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_agent_types_must_be_unique_single_worker() -> None:
    host_address = "localhost:50051"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker.start()

    await worker.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    with pytest.raises(ValueError):
        await worker.register_factory(
            type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
        )

    await worker.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)
    await worker.register_factory(type=AgentType("name5"), agent_factory=lambda: NoopAgent())

    await worker.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_agent_types_must_be_unique_multiple_workers() -> None:
    host_address = "localhost:50052"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker1 = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker1.start()
    worker2 = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker2.start()

    await worker1.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    with pytest.raises(Exception, match="Agent type name1 already registered"):
        await worker2.register_factory(
            type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
        )

    await worker2.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

    await worker1.stop()
    await worker2.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    host_address = "localhost:50053"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker1 = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker1.start()
    worker1.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker1.register_factory(
        type=AgentType("name1"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
    )
    await worker1.add_subscription(TypeSubscription("default", "name1"))

    worker2 = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker2.start()
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


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_register_doesnt_receive_after_removing_subscription() -> None:
    host_address = "localhost:50053"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker1 = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker1.start()
    worker1.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker1.register_factory(
        type=AgentType("name1"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
    )
    sub = DefaultSubscription(agent_type="name1")
    await worker1.add_subscription(sub)

    agent_1_instance = await worker1.try_get_underlying_agent_instance(AgentId("name1", "default"), LoopbackAgent)
    # Publish message from worker1
    await worker1.publish_message(MessageType(), topic_id=DefaultTopicId())

    # Let the agent run for a bit.
    await agent_1_instance.event.wait()
    agent_1_instance.event.clear()

    # Agents in default topic source should have received the message.
    assert agent_1_instance.num_calls == 1

    await worker1.remove_subscription(sub.id)

    # Publish message from worker1
    await worker1.publish_message(MessageType(), topic_id=DefaultTopicId())

    # Let the agent run for a bit.
    await asyncio.sleep(2)

    # Agent should not have received the message.
    assert agent_1_instance.num_calls == 1

    await worker1.stop()
    await host.stop()


@pytest.mark.asyncio
async def test_register_receives_publish_cascade_single_worker() -> None:
    host_address = "localhost:50054"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = GrpcWorkerAgentRuntime(host_address=host_address)
    await runtime.start()

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


@pytest.mark.grpc
@pytest.mark.skip(reason="Fix flakiness")
@pytest.mark.asyncio
async def test_register_receives_publish_cascade_multiple_workers() -> None:
    logging.basicConfig(level=logging.DEBUG)
    host_address = "localhost:50055"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    # TODO: Increasing num_initial_messages or max_round to 2 causes the test to fail.
    num_agents = 2
    num_initial_messages = 1
    max_rounds = 1
    total_num_calls_expected = 0
    for i in range(0, max_rounds):
        total_num_calls_expected += num_initial_messages * ((num_agents - 1) ** i)

    # Run multiple workers one for each agent.
    workers: List[GrpcWorkerAgentRuntime] = []
    # Register agents
    for i in range(num_agents):
        runtime = GrpcWorkerAgentRuntime(host_address=host_address)
        await runtime.start()
        await CascadingAgent.register(runtime, f"name{i}", lambda: CascadingAgent(max_rounds))
        workers.append(runtime)

    # Publish messages
    publisher = GrpcWorkerAgentRuntime(host_address=host_address)
    publisher.add_message_serializer(try_get_known_serializers_for_type(CascadingMessageType))
    await publisher.start()
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


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_default_subscription() -> None:
    host_address = "localhost:50056"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker.start()
    publisher = GrpcWorkerAgentRuntime(host_address=host_address)
    publisher.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await publisher.start()

    await LoopbackAgentWithDefaultSubscription.register(worker, "name", lambda: LoopbackAgentWithDefaultSubscription())

    await publisher.publish_message(MessageType(), topic_id=DefaultTopicId())

    await asyncio.sleep(2)

    # Agent in default topic source should have received the message.
    long_running_agent = await worker.try_get_underlying_agent_instance(
        AgentId("name", "default"), type=LoopbackAgentWithDefaultSubscription
    )
    assert long_running_agent.num_calls == 1

    # Agent in other topic source should not have received the message.
    other_long_running_agent = await worker.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithDefaultSubscription
    )
    assert other_long_running_agent.num_calls == 0

    await worker.stop()
    await publisher.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_default_subscription_other_source() -> None:
    host_address = "localhost:50057"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    runtime = GrpcWorkerAgentRuntime(host_address=host_address)
    await runtime.start()
    publisher = GrpcWorkerAgentRuntime(host_address=host_address)
    publisher.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await publisher.start()

    await LoopbackAgentWithDefaultSubscription.register(runtime, "name", lambda: LoopbackAgentWithDefaultSubscription())

    await publisher.publish_message(MessageType(), topic_id=DefaultTopicId(source="other"))

    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", "default"), type=LoopbackAgentWithDefaultSubscription
    )
    assert long_running_agent.num_calls == 0

    # Agent in other namespace should not have received the message
    other_long_running_agent = await runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithDefaultSubscription
    )
    assert other_long_running_agent.num_calls == 1

    await runtime.stop()
    await publisher.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_type_subscription() -> None:
    host_address = "localhost:50058"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    await worker.start()
    publisher = GrpcWorkerAgentRuntime(host_address=host_address)
    publisher.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await publisher.start()

    @type_subscription("Other")
    class LoopbackAgentWithSubscription(LoopbackAgent): ...

    await LoopbackAgentWithSubscription.register(worker, "name", lambda: LoopbackAgentWithSubscription())

    await publisher.publish_message(MessageType(), topic_id=TopicId(type="Other", source="default"))

    await asyncio.sleep(2)

    # Agent in default topic source should have received the message.
    long_running_agent = await worker.try_get_underlying_agent_instance(
        AgentId("name", "default"), type=LoopbackAgentWithSubscription
    )
    assert long_running_agent.num_calls == 1

    # Agent in other topic source should not have received the message.
    other_long_running_agent = await worker.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=LoopbackAgentWithSubscription
    )
    assert other_long_running_agent.num_calls == 0

    await worker.stop()
    await publisher.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_duplicate_subscription() -> None:
    host_address = "localhost:50059"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    worker1 = GrpcWorkerAgentRuntime(host_address=host_address)
    worker1_2 = GrpcWorkerAgentRuntime(host_address=host_address)
    host.start()
    try:
        await worker1.start()
        await NoopAgent.register(worker1, "worker1", lambda: NoopAgent())

        await worker1_2.start()

        # Note: This passes because worker1 is still running
        with pytest.raises(Exception, match="Agent type worker1 already registered"):
            await NoopAgent.register(worker1_2, "worker1", lambda: NoopAgent())

        # This is somehow covered in test_disconnected_agent as well as a stop will also disconnect the agent.
        #  Will keep them both for now as we might replace the way we simulate a disconnect
        await worker1.stop()

        with pytest.raises(ValueError):
            await NoopAgent.register(worker1_2, "worker1", lambda: NoopAgent())

    except Exception as ex:
        raise ex
    finally:
        await worker1_2.stop()
        await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_disconnected_agent() -> None:
    host_address = "localhost:50060"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    worker1 = GrpcWorkerAgentRuntime(host_address=host_address)
    worker1_2 = GrpcWorkerAgentRuntime(host_address=host_address)

    # TODO: Implementing `get_current_subscriptions` and `get_subscribed_recipients` requires access
    # to some private properties. This needs to be updated once they are available publicly

    def get_current_subscriptions() -> List[Subscription]:
        return host._servicer._subscription_manager._subscriptions  # type: ignore[reportPrivateUsage]

    async def get_subscribed_recipients() -> List[AgentId]:
        return await host._servicer._subscription_manager.get_subscribed_recipients(DefaultTopicId())  # type: ignore[reportPrivateUsage]

    try:
        await worker1.start()
        await LoopbackAgentWithDefaultSubscription.register(
            worker1, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
        )

        subscriptions1 = get_current_subscriptions()
        assert len(subscriptions1) == 2
        recipients1 = await get_subscribed_recipients()
        assert AgentId(type="worker1", key="default") in recipients1

        first_subscription_id = subscriptions1[0].id

        await worker1.publish_message(ContentMessage(content="Hello!"), DefaultTopicId())
        # This is a simple simulation of worker disconnct
        if worker1._host_connection is not None:  # type: ignore[reportPrivateUsage]
            try:
                await worker1._host_connection.close()  # type: ignore[reportPrivateUsage]
            except asyncio.CancelledError:
                pass

        await asyncio.sleep(1)

        subscriptions2 = get_current_subscriptions()
        assert len(subscriptions2) == 0
        recipients2 = await get_subscribed_recipients()
        assert len(recipients2) == 0
        await asyncio.sleep(1)

        await worker1_2.start()
        await LoopbackAgentWithDefaultSubscription.register(
            worker1_2, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
        )

        subscriptions3 = get_current_subscriptions()
        assert len(subscriptions3) == 2
        assert first_subscription_id not in [x.id for x in subscriptions3]

        recipients3 = await get_subscribed_recipients()
        assert len(set(recipients2)) == len(recipients2)  # Make sure there are no duplicates
        assert AgentId(type="worker1", key="default") in recipients3
    except Exception as ex:
        raise ex
    finally:
        await worker1.stop()
        await worker1_2.stop()


@default_subscription
class ProtoReceivingAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls = 0
        self.received_messages: list[Any] = []

    @event
    async def on_new_message(self, message: ProtoMessage, ctx: MessageContext) -> None:  # type: ignore
        self.num_calls += 1
        self.received_messages.append(message)


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_proto_payloads() -> None:
    host_address = "localhost:50057"
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    receiver_runtime = GrpcWorkerAgentRuntime(
        host_address=host_address, payload_serialization_format=PROTOBUF_DATA_CONTENT_TYPE
    )
    await receiver_runtime.start()
    publisher_runtime = GrpcWorkerAgentRuntime(
        host_address=host_address, payload_serialization_format=PROTOBUF_DATA_CONTENT_TYPE
    )
    publisher_runtime.add_message_serializer(try_get_known_serializers_for_type(ProtoMessage))
    await publisher_runtime.start()

    await ProtoReceivingAgent.register(receiver_runtime, "name", ProtoReceivingAgent)

    await publisher_runtime.publish_message(ProtoMessage(message="Hello!"), topic_id=DefaultTopicId())

    await asyncio.sleep(2)

    # Agent in default namespace should have received the message
    long_running_agent = await receiver_runtime.try_get_underlying_agent_instance(
        AgentId("name", "default"), type=ProtoReceivingAgent
    )
    assert long_running_agent.num_calls == 1
    assert long_running_agent.received_messages[0].message == "Hello!"

    # Agent in other namespace should not have received the message
    other_long_running_agent = await receiver_runtime.try_get_underlying_agent_instance(
        AgentId("name", key="other"), type=ProtoReceivingAgent
    )
    assert other_long_running_agent.num_calls == 0
    assert len(other_long_running_agent.received_messages) == 0

    await receiver_runtime.stop()
    await publisher_runtime.stop()
    await host.stop()


# TODO add tests for failure to deserialize


@pytest.mark.grpc
@pytest.mark.asyncio
@pytest.mark.skip(reason="Fix flakiness")
async def test_grpc_max_message_size() -> None:
    default_max_size = 2**22
    new_max_size = default_max_size * 2
    small_message = ContentMessage(content="small message")
    big_message = ContentMessage(content="." * (default_max_size + 1))

    extra_grpc_config = [
        ("grpc.max_send_message_length", new_max_size),
        ("grpc.max_receive_message_length", new_max_size),
    ]
    host_address = "localhost:50061"
    host = GrpcWorkerAgentRuntimeHost(address=host_address, extra_grpc_config=extra_grpc_config)
    worker1 = GrpcWorkerAgentRuntime(host_address=host_address, extra_grpc_config=extra_grpc_config)
    worker2 = GrpcWorkerAgentRuntime(host_address=host_address)
    worker3 = GrpcWorkerAgentRuntime(host_address=host_address, extra_grpc_config=extra_grpc_config)

    try:
        host.start()
        await worker1.start()
        await worker2.start()
        await worker3.start()
        await LoopbackAgentWithDefaultSubscription.register(
            worker1, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
        )
        await LoopbackAgentWithDefaultSubscription.register(
            worker2, "worker2", lambda: LoopbackAgentWithDefaultSubscription()
        )
        await LoopbackAgentWithDefaultSubscription.register(
            worker3, "worker3", lambda: LoopbackAgentWithDefaultSubscription()
        )

        # with pytest.raises(Exception):
        await worker1.publish_message(small_message, DefaultTopicId())
        # This is a simple simulation of worker disconnct
        await asyncio.sleep(1)
        agent_instance_2 = await worker2.try_get_underlying_agent_instance(
            AgentId("worker2", key="default"), type=LoopbackAgent
        )
        agent_instance_3 = await worker3.try_get_underlying_agent_instance(
            AgentId("worker3", key="default"), type=LoopbackAgent
        )
        assert agent_instance_2.num_calls == 1
        assert agent_instance_3.num_calls == 1

        await worker1.publish_message(big_message, DefaultTopicId())
        await asyncio.sleep(2)
        assert agent_instance_2.num_calls == 1  # Worker 2 won't receive the big message
        assert agent_instance_3.num_calls == 2  # Worker 3 will receive the big message as has increased message length
    except Exception as e:
        raise e
    finally:
        await worker1.stop()
        # await worker2.stop() # Worker 2 somehow breaks can can not be stopped.
        await worker3.stop()

        await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_agent_type_register_instance() -> None:
    host_address = "localhost:50051"
    agent1_id = AgentId(type="name", key="default")
    agentdup_id = AgentId(type="name", key="default")
    agent2_id = AgentId(type="name", key="notdefault")
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    agent1 = NoopAgent()
    agent2 = NoopAgent()
    agentdup = NoopAgent()
    await worker.start()

    await worker.register_agent_instance(agent1, agent_id=agent1_id)
    await worker.register_agent_instance(agent2, agent_id=agent2_id)

    with pytest.raises(ValueError):
        await worker.register_agent_instance(agentdup, agent_id=agentdup_id)

    assert await worker.try_get_underlying_agent_instance(agent1_id, type=NoopAgent) == agent1
    assert await worker.try_get_underlying_agent_instance(agent2_id, type=NoopAgent) == agent2

    await worker.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_agent_type_register_instance_different_types() -> None:
    host_address = "localhost:50051"
    agent1_id = AgentId(type="name", key="noop")
    agent2_id = AgentId(type="name", key="loopback")
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    agent1 = NoopAgent()
    agent2 = LoopbackAgent()
    await worker.start()

    await worker.register_agent_instance(agent1, agent_id=agent1_id)
    with pytest.raises(ValueError):
        await worker.register_agent_instance(agent2, agent_id=agent2_id)

    await worker.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_register_instance_factory() -> None:
    host_address = "localhost:50051"
    agent1_id = AgentId(type="name", key="default")
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    agent1 = NoopAgent()
    await worker.start()

    await agent1.register_instance(runtime=worker, agent_id=agent1_id)

    with pytest.raises(ValueError):
        await NoopAgent.register(runtime=worker, type="name", factory=lambda: NoopAgent())

    await worker.stop()
    await host.stop()


@pytest.mark.grpc
@pytest.mark.asyncio
async def test_instance_factory_messaging() -> None:
    host_address = "localhost:50051"
    loopback_agent_id = AgentId(type="dm_agent", key="dm_agent")
    cascading_agent_id = AgentId(type="instance_agent", key="instance_agent")
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()

    worker = GrpcWorkerAgentRuntime(host_address=host_address)
    cascading_agent = CascadingAgent(max_rounds=5)
    loopback_agent = LoopbackAgent()
    await worker.start()

    await loopback_agent.register_instance(worker, agent_id=loopback_agent_id)
    resp = await worker.send_message(message=ContentMessage(content="Hello!"), recipient=loopback_agent_id)
    assert resp == ContentMessage(content="Hello!")

    await cascading_agent.register_instance(worker, agent_id=cascading_agent_id)
    await CascadingAgent.register(worker, "factory_agent", lambda: CascadingAgent(max_rounds=5))

    # instance_agent will publish a message that factory_agent will pick up
    for i in range(5):
        await worker.publish_message(
            CascadingMessageType(round=i + 1), TopicId(type="instance_agent", source="instance_agent")
        )
    await asyncio.sleep(2)

    agent = await worker.try_get_underlying_agent_instance(AgentId("factory_agent", "default"), CascadingAgent)
    assert agent.num_calls == 4
    assert cascading_agent.num_calls == 5

    await worker.stop()
    await host.stop()


# GrpcWorkerAgentRuntimeHost eats exceptions in the main loop
# @pytest.mark.grpc
# @pytest.mark.asyncio
# async def test_agent_type_register_instance_publish_new_source() -> None:
#     host_address = "localhost:50056"
#     agent_id = AgentId(type="name", key="default")
#     agent1 = LoopbackAgent()
#     host = GrpcWorkerAgentRuntimeHost(address=host_address)
#     host.start()
#     worker = GrpcWorkerAgentRuntime(host_address=host_address)
#     await worker.start()
#     publisher = GrpcWorkerAgentRuntime(host_address=host_address)
#     publisher.add_message_serializer(try_get_known_serializers_for_type(MessageType))
#     await publisher.start()

#     await agent1.register_instance(worker, agent_id=agent_id)
#     await worker.add_subscription(TypeSubscription("notdefault", "name"))

#     with pytest.raises(RuntimeError):
#         await worker.publish_message(MessageType(), TopicId("notdefault", "notdefault"))
#         await asyncio.sleep(2)

#     await worker.stop()
#     await host.stop()

if __name__ == "__main__":
    os.environ["GRPC_VERBOSITY"] = "DEBUG"
    os.environ["GRPC_TRACE"] = "all"

    asyncio.run(test_disconnected_agent())
    asyncio.run(test_grpc_max_message_size())
