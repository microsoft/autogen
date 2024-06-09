from typing import Any, Sequence

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.core import AgentRuntime, BaseAgent, CancellationToken


class NoopAgent(BaseAgent): # type: ignore
    def __init__(self, name: str, router: AgentRuntime) -> None: # type: ignore
        super().__init__(name, "A no op agent", router)

    @property
    def subscriptions(self) -> Sequence[type]:
        return []

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any: # type: ignore
        raise NotImplementedError


@pytest.mark.asyncio
async def test_agent_names_must_be_unique() -> None:
    router = SingleThreadedAgentRuntime()

    _agent1 = NoopAgent("name1", router)

    with pytest.raises(ValueError):
        _agent1_again = NoopAgent("name1", router)

    _agent3 = NoopAgent("name3", router)


