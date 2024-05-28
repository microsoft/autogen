from typing import Any, Mapping, Sequence
import pytest

from agnext.application_components import SingleThreadedAgentRuntime
from agnext.core import AgentRuntime
from agnext.core import BaseAgent
from agnext.core import CancellationToken

class StatefulAgent(BaseAgent):
    def __init__(self, name: str, runtime: AgentRuntime) -> None:
        super().__init__(name, runtime)
        self.state = 0

    @property
    def subscriptions(self) -> Sequence[type]:
        return []

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any:
        raise NotImplementedError

    def save_state(self) -> Mapping[str, Any]:
        return {"state": self.state}

    def load_state(self, state: Mapping[str, Any]) -> None:
        self.state = state["state"]


@pytest.mark.asyncio
async def test_agent_can_save_state() -> None:
    runtime = SingleThreadedAgentRuntime()

    agent1 = StatefulAgent("name1", runtime)
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

    agent1 = StatefulAgent("name1", runtime)
    assert agent1.state == 0
    agent1.state = 1
    assert agent1.state == 1

    runtime_state = runtime.save_state()

    runtime2 = SingleThreadedAgentRuntime()
    agent2 = StatefulAgent("name1", runtime2)
    runtime2.load_state(runtime_state)
    assert agent2.state == 1



