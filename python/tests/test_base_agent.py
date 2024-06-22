import pytest
from pytest_mock import MockerFixture
from agnext.core import AgentRuntime, agent_instantiation_context, AgentId

from test_utils import NoopAgent



@pytest.mark.asyncio
async def test_base_agent_create(mocker: MockerFixture) -> None:
    runtime = mocker.Mock(spec=AgentRuntime)

    # Shows how to set the context for the agent instantiation in a test context
    agent_instantiation_context.set((runtime, AgentId("name", "namespace")))

    agent = NoopAgent()
    assert agent.runtime == runtime
    assert agent.id == AgentId("name", "namespace")

