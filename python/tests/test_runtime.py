import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.core import AgentId, AgentInstantiationContext
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

    agent1 = await runtime.register_and_get("name1", agent_factory)
    assert agent1 == AgentId("name1", "default")

    with pytest.raises(ValueError):
        _agent1 = await runtime.register_and_get("name1", NoopAgent)

    _agent1 = await runtime.register_and_get("name3", NoopAgent)


@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name", LoopbackAgent)
    run_context = runtime.start()
    await runtime.publish_message(MessageType(), namespace="default")

    await run_context.stop_when_idle()

    # Agent in default namespace should have received the message
    long_running_agent = await runtime.try_get_underlying_agent_instance(await runtime.get("name"), type=LoopbackAgent)
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = await runtime.try_get_underlying_agent_instance(await runtime.get("name", namespace="other"), type=LoopbackAgent)
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

    run_context = runtime.start()

    # Publish messages
    for _ in range(num_initial_messages):
        await runtime.publish_message(CascadingMessageType(round=1), namespace="default")

    # Process until idle.
    await run_context.stop_when_idle()

    # Check that each agent received the correct number of messages.
    for i in range(num_agents):
        agent = await runtime.try_get_underlying_agent_instance(await runtime.get(f"name{i}"), CascadingAgent)
        assert agent.num_calls == total_num_calls_expected
