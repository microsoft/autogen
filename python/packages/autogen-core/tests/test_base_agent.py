import pytest
from autogen_core import AgentId, AgentInstantiationContext, AgentRuntime
from autogen_test_utils import NoopAgent
from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_base_agent_create(mocker: MockerFixture) -> None:
    runtime = mocker.Mock(spec=AgentRuntime)

    # Shows how to set the context for the agent instantiation in a test context
    with AgentInstantiationContext.populate_context((runtime, AgentId("name2", "namespace2"))):
        agent2 = NoopAgent()
        assert agent2.runtime == runtime
        assert agent2.id == AgentId("name2", "namespace2")
