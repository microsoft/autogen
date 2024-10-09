from typing import Any, Mapping

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, BaseAgent, MessageContext


class StatefulAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("A stateful agent")
        self.state = 0

    async def on_message(self, message: Any, ctx: MessageContext) -> None:
        raise NotImplementedError

    def save_state(self) -> Mapping[str, Any]:
        return {"state": self.state}

    def load_state(self, state: Mapping[str, Any]) -> None:
        self.state = state["state"]


@pytest.mark.asyncio
async def test_agent_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name1", StatefulAgent)
    agent1_id = AgentId("name1", key="default")
    agent1: StatefulAgent = await runtime.try_get_underlying_agent_instance(agent1_id, type=StatefulAgent)
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    agent1_state = agent1.save_state()

    agent1.state = 2
    assert agent1.state == 2

    agent1.load_state(agent1_state)
    assert agent1.state == 1


@pytest.mark.asyncio
async def test_runtime_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    await runtime.register("name1", StatefulAgent)
    agent1_id = AgentId("name1", key="default")
    agent1: StatefulAgent = await runtime.try_get_underlying_agent_instance(agent1_id, type=StatefulAgent)
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    runtime_state = await runtime.save_state()

    runtime2 = SingleThreadedAgentRuntime()
    await runtime2.register("name1", StatefulAgent)
    agent2_id = AgentId("name1", key="default")
    agent2: StatefulAgent = await runtime2.try_get_underlying_agent_instance(agent2_id, type=StatefulAgent)

    await runtime2.load_state(runtime_state)
    assert agent2.state == 1
