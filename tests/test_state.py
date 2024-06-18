from typing import Any, Mapping, Sequence

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.core import BaseAgent, CancellationToken


class StatefulAgent(BaseAgent): # type: ignore
    def __init__(self) -> None: # type: ignore
        super().__init__("A stateful agent", [])
        self.state = 0

    @property
    def subscriptions(self) -> Sequence[type]:
        return []

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any: # type: ignore
        raise NotImplementedError

    def save_state(self) -> Mapping[str, Any]:
        return {"state": self.state}

    def load_state(self, state: Mapping[str, Any]) -> None:
        self.state = state["state"]


@pytest.mark.asyncio
async def test_agent_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    agent1_id = runtime.register_and_get("name1", StatefulAgent)
    agent1: StatefulAgent = runtime._get_agent(agent1_id) # type: ignore
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

    agent1_id = runtime.register_and_get("name1", StatefulAgent)
    agent1: StatefulAgent = runtime._get_agent(agent1_id) # type: ignore
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    runtime_state = runtime.save_state()

    runtime2 = SingleThreadedAgentRuntime()
    agent2_id = runtime2.register_and_get("name1", StatefulAgent)
    agent2: StatefulAgent = runtime2._get_agent(agent2_id) # type: ignore

    runtime2.load_state(runtime_state)
    assert agent2.state == 1



