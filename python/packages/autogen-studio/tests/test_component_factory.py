import pytest
from typing import List

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.task import MaxMessageTermination, StopMessageTermination, TextMentionTermination
from autogen_core.components.tools import FunctionTool

from autogenstudio.datamodel.types import (
    AgentConfig, ModelConfig, TeamConfig, ToolConfig, TerminationConfig,
    ModelTypes, AgentTypes, TeamTypes, TerminationTypes, ToolTypes,
    ComponentTypes
)
from autogenstudio.database import ComponentFactory


@pytest.fixture
def component_factory():
    return ComponentFactory()


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
""",
        tool_type=ToolTypes.PYTHON_FUNCTION,
        component_type=ComponentTypes.TOOL,
        version="1.0.0"
    )


@pytest.fixture
def sample_model_config():
    return ModelConfig(
        model_type=ModelTypes.OPENAI,
        model="gpt-4",
        api_key="test-key",
        component_type=ComponentTypes.MODEL,
        version="1.0.0"
    )


@pytest.fixture
def sample_agent_config(sample_model_config: ModelConfig, sample_tool_config: ToolConfig):
    return AgentConfig(
        name="test_agent",
        agent_type=AgentTypes.ASSISTANT,
        system_message="You are a helpful assistant",
        model_client=sample_model_config,
        tools=[sample_tool_config],
        component_type=ComponentTypes.AGENT,
        version="1.0.0"
    )


@pytest.fixture
def sample_termination_config():
    return TerminationConfig(
        termination_type=TerminationTypes.MAX_MESSAGES,
        max_messages=10,
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )


@pytest.fixture
def sample_team_config(sample_agent_config: AgentConfig, sample_termination_config: TerminationConfig, sample_model_config: ModelConfig):
    return TeamConfig(
        name="test_team",
        team_type=TeamTypes.ROUND_ROBIN,
        participants=[sample_agent_config],
        termination_condition=sample_termination_config,
        model_client=sample_model_config,
        component_type=ComponentTypes.TEAM,
        version="1.0.0"
    )


@pytest.mark.asyncio
async def test_load_tool(component_factory: ComponentFactory, sample_tool_config: ToolConfig):
    # Test loading tool from ToolConfig
    tool = await component_factory.load_tool(sample_tool_config)
    assert isinstance(tool, FunctionTool)
    assert tool.name == "calculator"
    assert tool.description == "A simple calculator function"

    # Test tool functionality
    result = tool._func(5, 3, '+')
    assert result == 8


@pytest.mark.asyncio
async def test_load_tool_invalid_config(component_factory: ComponentFactory):
    # Test with missing required fields
    with pytest.raises(ValueError):
        await component_factory.load_tool(ToolConfig(
            name="test",
            description="",
            content="",
            tool_type=ToolTypes.PYTHON_FUNCTION,
            component_type=ComponentTypes.TOOL,
            version="1.0.0"
        ))

    # Test with invalid Python code
    invalid_config = ToolConfig(
        name="invalid",
        description="Invalid function",
        content="def invalid_func(): return invalid syntax",
        tool_type=ToolTypes.PYTHON_FUNCTION,
        component_type=ComponentTypes.TOOL,
        version="1.0.0"
    )
    with pytest.raises(ValueError):
        await component_factory.load_tool(invalid_config)


@pytest.mark.asyncio
async def test_load_model(component_factory: ComponentFactory, sample_model_config: ModelConfig):
    # Test loading model from ModelConfig
    model = await component_factory.load_model(sample_model_config)
    assert model is not None


@pytest.mark.asyncio
async def test_load_agent(component_factory: ComponentFactory, sample_agent_config: AgentConfig):
    # Test loading agent from AgentConfig
    agent = await component_factory.load_agent(sample_agent_config)
    assert isinstance(agent, AssistantAgent)
    assert agent.name == "test_agent"
    assert len(agent._tools) == 1


@pytest.mark.asyncio
async def test_load_termination(component_factory: ComponentFactory):
    # Test MaxMessageTermination
    max_msg_config = TerminationConfig(
        termination_type=TerminationTypes.MAX_MESSAGES,
        max_messages=5,
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )
    termination = await component_factory.load_termination(max_msg_config)
    assert isinstance(termination, MaxMessageTermination)
    assert termination._max_messages == 5

    # Test StopMessageTermination
    stop_msg_config = TerminationConfig(
        termination_type=TerminationTypes.STOP_MESSAGE,
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )
    termination = await component_factory.load_termination(stop_msg_config)
    assert isinstance(termination, StopMessageTermination)

    # Test TextMentionTermination
    text_mention_config = TerminationConfig(
        termination_type=TerminationTypes.TEXT_MENTION,
        text="DONE",
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )
    termination = await component_factory.load_termination(text_mention_config)
    assert isinstance(termination, TextMentionTermination)
    assert termination._text == "DONE"

    # Test AND combination
    and_combo_config = TerminationConfig(
        termination_type=TerminationTypes.COMBINATION,
        operator="and",
        conditions=[
            TerminationConfig(
                termination_type=TerminationTypes.MAX_MESSAGES,
                max_messages=5,
                component_type=ComponentTypes.TERMINATION,
                version="1.0.0"
            ),
            TerminationConfig(
                termination_type=TerminationTypes.TEXT_MENTION,
                text="DONE",
                component_type=ComponentTypes.TERMINATION,
                version="1.0.0"
            )
        ],
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )
    termination = await component_factory.load_termination(and_combo_config)
    assert termination is not None

    # Test OR combination
    or_combo_config = TerminationConfig(
        termination_type=TerminationTypes.COMBINATION,
        operator="or",
        conditions=[
            TerminationConfig(
                termination_type=TerminationTypes.MAX_MESSAGES,
                max_messages=5,
                component_type=ComponentTypes.TERMINATION,
                version="1.0.0"
            ),
            TerminationConfig(
                termination_type=TerminationTypes.TEXT_MENTION,
                text="DONE",
                component_type=ComponentTypes.TERMINATION,
                version="1.0.0"
            )
        ],
        component_type=ComponentTypes.TERMINATION,
        version="1.0.0"
    )
    termination = await component_factory.load_termination(or_combo_config)
    assert termination is not None

    # Test invalid combinations
    with pytest.raises(ValueError):
        await component_factory.load_termination(TerminationConfig(
            termination_type=TerminationTypes.COMBINATION,
            conditions=[],  # Empty conditions
            component_type=ComponentTypes.TERMINATION,
            version="1.0.0"
        ))

    with pytest.raises(ValueError):
        await component_factory.load_termination(TerminationConfig(
            termination_type=TerminationTypes.COMBINATION,
            operator="invalid",  # type: ignore
            conditions=[
                TerminationConfig(
                    termination_type=TerminationTypes.MAX_MESSAGES,
                    max_messages=5,
                    component_type=ComponentTypes.TERMINATION,
                    version="1.0.0"
                )
            ],
            component_type=ComponentTypes.TERMINATION,
            version="1.0.0"
        ))

    # Test missing operator
    with pytest.raises(ValueError):
        await component_factory.load_termination(TerminationConfig(
            termination_type=TerminationTypes.COMBINATION,
            conditions=[
                TerminationConfig(
                    termination_type=TerminationTypes.MAX_MESSAGES,
                    max_messages=5,
                    component_type=ComponentTypes.TERMINATION,
                    version="1.0.0"
                ),
                TerminationConfig(
                    termination_type=TerminationTypes.TEXT_MENTION,
                    text="DONE",
                    component_type=ComponentTypes.TERMINATION,
                    version="1.0.0"
                )
            ],
            component_type=ComponentTypes.TERMINATION,
            version="1.0.0"
        ))


@pytest.mark.asyncio
async def test_load_team(component_factory: ComponentFactory, sample_team_config: TeamConfig, sample_model_config: ModelConfig):
    # Test loading RoundRobinGroupChat team
    team = await component_factory.load_team(sample_team_config)
    assert isinstance(team, RoundRobinGroupChat)
    assert len(team._participants) == 1

    # Test loading SelectorGroupChat team with multiple participants
    selector_team_config = TeamConfig(
        name="selector_team",
        team_type=TeamTypes.SELECTOR,
        participants=[  # Add two participants
            sample_team_config.participants[0],  # First agent
            AgentConfig(  # Second agent
                name="test_agent_2",
                agent_type=AgentTypes.ASSISTANT,
                system_message="You are another helpful assistant",
                model_client=sample_model_config,
                tools=sample_team_config.participants[0].tools,
                component_type=ComponentTypes.AGENT,
                version="1.0.0"
            )
        ],
        termination_condition=sample_team_config.termination_condition,
        model_client=sample_model_config,
        component_type=ComponentTypes.TEAM,
        version="1.0.0"
    )
    team = await component_factory.load_team(selector_team_config)
    assert isinstance(team, SelectorGroupChat)
    assert len(team._participants) == 2


@pytest.mark.asyncio
async def test_invalid_configs(component_factory: ComponentFactory):
    # Test invalid agent type
    with pytest.raises(ValueError):
        await component_factory.load_agent(AgentConfig(
            name="test",
            agent_type="InvalidAgent",  # type: ignore
            system_message="test",
            component_type=ComponentTypes.AGENT,
            version="1.0.0"
        ))

    # Test invalid team type
    with pytest.raises(ValueError):
        await component_factory.load_team(TeamConfig(
            name="test",
            team_type="InvalidTeam",  # type: ignore
            participants=[],
            component_type=ComponentTypes.TEAM,
            version="1.0.0"
        ))

    # Test invalid termination type
    with pytest.raises(ValueError):
        await component_factory.load_termination(TerminationConfig(
            termination_type="InvalidTermination",  # type: ignore
            component_type=ComponentTypes.TERMINATION,
            version="1.0.0"
        ))
