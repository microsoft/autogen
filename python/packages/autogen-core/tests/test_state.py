from typing import Any, Mapping

import pytest
from autogen_core import AgentId, BaseAgent, MessageContext, SingleThreadedAgentRuntime


class StatefulAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("A stateful agent")
        self.state = 0

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> None:
        raise NotImplementedError

    async def save_state(self) -> Mapping[str, Any]:
        return {"state": self.state}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self.state = state["state"]


@pytest.mark.asyncio
async def test_agent_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    await StatefulAgent.register(runtime, "name1", StatefulAgent)
    agent1_id = AgentId("name1", key="default")
    agent1: StatefulAgent = await runtime.try_get_underlying_agent_instance(agent1_id, type=StatefulAgent)
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    agent1_state = await agent1.save_state()

    agent1.state = 2
    assert agent1.state == 2

    await agent1.load_state(agent1_state)
    assert agent1.state == 1


@pytest.mark.asyncio
async def test_runtime_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    await StatefulAgent.register(runtime, "name1", StatefulAgent)
    agent1_id = AgentId("name1", key="default")
    agent1: StatefulAgent = await runtime.try_get_underlying_agent_instance(agent1_id, type=StatefulAgent)
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    runtime_state = await runtime.save_state()

    runtime2 = SingleThreadedAgentRuntime()
    await StatefulAgent.register(runtime2, "name1", StatefulAgent)
    agent2_id = AgentId("name1", key="default")
    agent2: StatefulAgent = await runtime2.try_get_underlying_agent_instance(agent2_id, type=StatefulAgent)

    await runtime2.load_state(runtime_state)
    assert agent2.state == 1
