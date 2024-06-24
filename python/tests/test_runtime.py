import pytest

from agnext.application import SingleThreadedAgentRuntime
from agnext.core import AgentId, AgentRuntime
from test_utils import LoopbackAgent, MessageType, NoopAgent


@pytest.mark.asyncio
async def test_agent_names_must_be_unique() -> None:
    runtime = SingleThreadedAgentRuntime()

    def agent_factory(runtime: AgentRuntime, id: AgentId) -> NoopAgent:
        assert id == AgentId("name1", "default")
        agent = NoopAgent()
        assert agent.id == id
        return agent

    agent1 = runtime.register_and_get("name1", agent_factory)
    assert agent1 == AgentId("name1", "default")

    with pytest.raises(ValueError):
        _agent1 = runtime.register_and_get("name1", NoopAgent)

    _agent1 = runtime.register_and_get("name3", NoopAgent)

@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    runtime = SingleThreadedAgentRuntime()

    runtime.register("name", LoopbackAgent)
    await runtime.publish_message(MessageType(), namespace="default")

    while len(runtime.unprocessed_messages) > 0 or runtime.outstanding_tasks > 0:
        await runtime.process_next()

    # Agent in default namespace should have received the message
    long_running_agent: LoopbackAgent = runtime._get_agent(runtime.get("name")) # type: ignore
    assert long_running_agent.num_calls == 1

    # Agent in other namespace should not have received the message
    other_long_running_agent: LoopbackAgent = runtime._get_agent(runtime.get("name", namespace="other")) # type: ignore
    assert other_long_running_agent.num_calls == 0

