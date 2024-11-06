import pytest
from typing import List

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.task import MaxMessageTermination, StopMessageTermination, TextMentionTermination
from autogen_core.components.tools import FunctionTool

from autogenstudio.datamodel import (
    AgentConfig, ModelConfig, TeamConfig, ToolConfig, TerminationConfig, ModelTypes, AgentTypes, TeamTypes, TerminationTypes
)
from autogenstudio.database import AgentFactory


@pytest.fixture
def agent_factory():
    return AgentFactory()


@pytest.fixture
def sample_tool_config():
    return ToolConfig(
        name="calculator",
        description="A simple calculator function",
        content="""
def calculator(a: int, b: int, operation: str = '+') -> int:
    '''
    A simple calculator that performs basic operations
    '''
    if operation == '+':
        return a + b
    elif operation == '-':
        return a - b
    elif operation == '*':
        return a * b
    elif operation == '/':
        return a / b
    else:
        raise ValueError("Invalid operation")
"""
    )


@pytest.fixture
def sample_model_config():
    return ModelConfig(
        model_type=ModelTypes.openai,
        model="gpt-4",
        api_key="test-key"
    )


@pytest.fixture
def sample_agent_config(sample_model_config: ModelConfig, sample_tool_config: ToolConfig):
    return AgentConfig(
        name="test_agent",
        agent_type=AgentTypes.assistant,
        system_message="You are a helpful assistant",
        model_client=sample_model_config,
        tools=[sample_tool_config]
    )


@pytest.fixture
def sample_termination_config():
    return TerminationConfig(
        termination_type=TerminationTypes.max_messages,
        max_messages=10
    )


@pytest.fixture
def sample_team_config(sample_agent_config: AgentConfig, sample_termination_config: TerminationConfig, sample_model_config: ModelConfig):
    return TeamConfig(
        name="test_team",
        team_type=TeamTypes.round_robin,
        participants=[sample_agent_config],
        termination_condition=sample_termination_config,
        model_client=sample_model_config  # Add model_client
    )


def test_load_tool(agent_factory: AgentFactory, sample_tool_config: ToolConfig):
    # Test loading tool from ToolConfig
    tool = agent_factory.load_tool(sample_tool_config)
    assert isinstance(tool, FunctionTool)
    assert tool.name == "calculator"
    assert tool.description == "A simple calculator function"

    # Test tool functionality
    result = tool._func(5, 3, '+')
    assert result == 8


def test_load_tool_invalid_config(agent_factory: AgentFactory):
    # Test with missing required fields
    with pytest.raises(ValueError):
        agent_factory.load_tool(ToolConfig(
            name="test", description="", content=""))

    # Test with invalid Python code
    invalid_config = ToolConfig(
        name="invalid",
        description="Invalid function",
        content="def invalid_func(): return invalid syntax"
    )
    with pytest.raises(ValueError):
        agent_factory.load_tool(invalid_config)


def test_load_model(agent_factory: AgentFactory, sample_model_config: ModelConfig):
    # Test loading model from ModelConfig
    model = agent_factory.load_model(sample_model_config)
    assert model is not None


def test_load_agent(agent_factory: AgentFactory, sample_agent_config: AgentConfig):
    # Test loading agent from AgentConfig
    agent = agent_factory.load_agent(sample_agent_config)
    assert isinstance(agent, AssistantAgent)
    assert agent.name == "test_agent"
    assert len(agent._tools) == 1


def test_load_termination(agent_factory: AgentFactory):
    # Test MaxMessageTermination
    max_msg_config = TerminationConfig(
        termination_type=TerminationTypes.max_messages,
        max_messages=5
    )
    termination = agent_factory.load_termination(max_msg_config)
    assert isinstance(termination, MaxMessageTermination)
    assert termination._max_messages == 5

    # Test StopMessageTermination
    stop_msg_config = TerminationConfig(
        termination_type=TerminationTypes.stop_message
    )
    termination = agent_factory.load_termination(stop_msg_config)
    assert isinstance(termination, StopMessageTermination)

    # Test TextMentionTermination
    text_mention_config = TerminationConfig(
        termination_type=TerminationTypes.text_mention,
        text="DONE"
    )
    termination = agent_factory.load_termination(text_mention_config)
    assert isinstance(termination, TextMentionTermination)
    assert termination._text == "DONE"


def test_load_team(agent_factory: AgentFactory, sample_team_config: TeamConfig, sample_model_config: ModelConfig):
    # Test loading RoundRobinGroupChat team
    team = agent_factory.load_team(sample_team_config)
    assert isinstance(team, RoundRobinGroupChat)
    assert len(team._participants) == 1

    # Test loading SelectorGroupChat team with multiple participants
    selector_team_config = TeamConfig(
        name="selector_team",
        team_type=TeamTypes.selector,
        participants=[  # Add two participants
            sample_team_config.participants[0],  # First agent
            AgentConfig(  # Second agent
                name="test_agent_2",
                agent_type=AgentTypes.assistant,
                system_message="You are another helpful assistant",
                model_client=sample_model_config,
                # Reuse tools from first agent
                tools=sample_team_config.participants[0].tools
            )
        ],
        termination_condition=sample_team_config.termination_condition,
        model_client=sample_model_config
    )
    team = agent_factory.load_team(selector_team_config)
    assert isinstance(team, SelectorGroupChat)
    assert len(team._participants) == 2  # Verify we have two participants


def test_invalid_configs(agent_factory: AgentFactory):
    # Test invalid agent type
    with pytest.raises(ValueError):
        agent_factory.load_agent(AgentConfig(
            name="test",
            agent_type="InvalidAgent",  # type: ignore
            system_message="test"
        ))

    # Test invalid team type
    with pytest.raises(ValueError):
        agent_factory.load_team(TeamConfig(
            name="test",
            team_type="InvalidTeam",  # type: ignore
            participants=[]
        ))

    # Test invalid termination type
    with pytest.raises(ValueError):
        agent_factory.load_termination(TerminationConfig(
            termination_type="InvalidTermination"  # type: ignore
        ))
