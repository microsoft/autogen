import pytest
from pytest_mock import MockerFixture
from agnext.core import AgentRuntime, AGENT_INSTANTIATION_CONTEXT_VAR, AgentId

from test_utils import NoopAgent



@pytest.mark.asyncio
async def test_base_agent_create(mocker: MockerFixture) -> None:
    runtime = mocker.Mock(spec=AgentRuntime)

    # Shows how to set the context for the agent instantiation in a test context
    AGENT_INSTANTIATION_CONTEXT_VAR.set((runtime, AgentId("name", "namespace")))

    agent = NoopAgent()
    assert agent.runtime == runtime
    assert agent.id == AgentId("name", "namespace")

