from typing import AsyncGenerator

import pytest
import pytest_asyncio
from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import AgentRuntime, SingleThreadedAgentRuntime
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest_asyncio.fixture(params=["single_threaded", "embedded"])  # type: ignore
async def runtime(request: pytest.FixtureRequest) -> AsyncGenerator[AgentRuntime | None, None]:
    if request.param == "single_threaded":
        runtime = SingleThreadedAgentRuntime()
        runtime.start()
        yield runtime
        await runtime.stop()
    elif request.param == "embedded":
        yield None


@pytest.mark.asyncio
async def test_society_of_mind_agent(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["1", "2", "3"],
    )
    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(3)
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)
    response = await society_of_mind_agent.run(task="Count to 10.")
    assert len(response.messages) == 2
    assert response.messages[0].source == "user"
    assert response.messages[1].source == "society_of_mind"

    # Test save and load state.
    state = await society_of_mind_agent.save_state()
    assert state is not None
    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(3)
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent2 = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)
    await society_of_mind_agent2.load_state(state)
    state2 = await society_of_mind_agent2.save_state()
    assert state == state2

    # Test serialization.
    soc_agent_config = society_of_mind_agent.dump_component()
    assert soc_agent_config.provider == "autogen_agentchat.agents.SocietyOfMindAgent"

    # Test deserialization.
    loaded_soc_agent = SocietyOfMindAgent.load_component(soc_agent_config)
    assert isinstance(loaded_soc_agent, SocietyOfMindAgent)
    assert loaded_soc_agent.name == "society_of_mind"
