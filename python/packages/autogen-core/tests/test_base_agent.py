import pytest
from autogen_core.base import AgentId, AgentInstantiationContext, AgentRuntime
from pytest_mock import MockerFixture
from test_utils import NoopAgent


@pytest.mark.asyncio
async def test_base_agent_create(mocker: MockerFixture) -> None:
    runtime = mocker.Mock(spec=AgentRuntime)

    # Shows how to set the context for the agent instantiation in a test context
    with AgentInstantiationContext.populate_context((runtime, AgentId("name", "namespace"))):
        agent = NoopAgent()
        assert agent.runtime == runtime
        assert agent.id == AgentId("name", "namespace")
