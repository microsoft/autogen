import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent, ToolCallRequestEvent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.tools import AgentTool, TeamTool
from autogen_core import (
    CancellationToken,
    FunctionCall,
)
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient
from test_group_chat import _EchoAgent  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_agent_tool_run() -> None:
    """Test running a task with AgentTool."""
    mock_chat_agent = _EchoAgent("Mock_Agent", "A mock agent for testing")
    tool = AgentTool(agent=mock_chat_agent)
    task_result = await tool.run_json({"task": "Test task"}, cancellation_token=CancellationToken())
    assert task_result.messages[1].content == "Test task"


@pytest.mark.asyncio
async def test_agent_tool_state() -> None:
    """Test saving state of AgentTool."""
    mock_chat_agent = _EchoAgent("Mock_Agent", "A mock agent for testing")
    tool = AgentTool(agent=mock_chat_agent)
    state = await tool.save_state_json()
    assert state == {"last_message": None, "total_messages": 0}

    await tool.run_json({"task": "Test task"}, cancellation_token=CancellationToken())
    state = await tool.save_state_json()
    assert state == {"last_message": "Test task", "total_messages": 1}

    mock_chat_agent_2 = _EchoAgent("Mock_Agent_2", "A mock agent for testing")
    tool_2 = AgentTool(agent=mock_chat_agent_2)
    await tool_2.load_state_json(state)
    state2 = await tool_2.save_state_json()
    assert state2 == {"last_message": "Test task", "total_messages": 1}


def test_agent_tool_component() -> None:
    """Test serialization of AgentTool to config."""
    model_client = ReplayChatCompletionClient(["test"])
    agent = AssistantAgent(name="assistant", model_client=model_client)
    tool = AgentTool(agent=agent)
    config = tool.dump_component()
    assert config.provider == "autogen_agentchat.tools.AgentTool"

    tool2 = AgentTool.load_component(config)
    assert isinstance(tool2, AgentTool)
    assert tool2.name == agent.name
    assert tool2.description == agent.description


@pytest.mark.asyncio
async def test_team_tool() -> None:
    """Test running a task with TeamTool."""
    agent1 = _EchoAgent("Agent1", "An agent for testing")
    agent2 = _EchoAgent("Agent2", "Another agent for testing")
    termination = MaxMessageTermination(max_messages=3)
    team = RoundRobinGroupChat(
        [agent1, agent2],
        termination_condition=termination,
    )
    tool = TeamTool(team=team, name="Team Tool", description="A team tool for testing")
    task_result = await tool.run_json(args={"task": "test task"}, cancellation_token=CancellationToken())
    assert task_result.messages[1].content == "test task"
    assert task_result.messages[2].content == "test task"

    # Validate state.
    state = await tool.save_state_json()
    # Reload the state and check if it matches.
    agent2 = _EchoAgent("Agent1", "Another agent for testing")
    agent3 = _EchoAgent("Agent2", "Another agent for testing")
    team2 = RoundRobinGroupChat(
        [agent2, agent3],
        termination_condition=termination,
    )
    tool2 = TeamTool(team=team2, name="Team Tool", description="A team tool for testing")
    await tool2.load_state_json(state)
    state2 = await tool2.save_state_json()
    assert state == state2


@pytest.mark.asyncio
async def test_team_tool_component() -> None:
    """Test serialization of TeamTool to config."""
    model_client = ReplayChatCompletionClient(["test"])
    agent1 = AssistantAgent(name="assistant1", model_client=model_client)
    agent2 = AssistantAgent(name="assistant2", model_client=model_client)
    team = RoundRobinGroupChat([agent1, agent2])
    tool = TeamTool(team=team, name="Team Tool", description="A team tool for testing")
    config = tool.dump_component()
    assert config.provider == "autogen_agentchat.tools.TeamTool"

    tool2 = TeamTool.load_component(config)
    assert isinstance(tool2, TeamTool)
    assert tool2.name == "Team Tool"
    assert tool2.description == "A team tool for testing"
    assert isinstance(tool2._team, RoundRobinGroupChat)  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_agent_tool_stream() -> None:
    """Test running a task with AgentTool in streaming mode."""

    def _query_function() -> str:
        return "Test task"

    tool_agent_model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                content=[FunctionCall(name="query_function", arguments="{}", id="1")],
                finish_reason="function_calls",
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Summary from tool agent",
        ],
        model_info={
            "family": "gpt-41",
            "function_calling": True,
            "json_output": True,
            "multiple_system_messages": True,
            "structured_output": True,
            "vision": True,
        },
    )
    tool_agent = AssistantAgent(
        name="tool_agent",
        model_client=tool_agent_model_client,
        tools=[_query_function],
        reflect_on_tool_use=True,
        description="An agent for testing",
    )
    tool = AgentTool(tool_agent)

    main_agent_model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                content=[FunctionCall(id="1", name="tool_agent", arguments='{"task": "Input task from main agent"}')],
                finish_reason="function_calls",
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Summary from main agent",
        ],
        model_info={
            "family": "gpt-41",
            "function_calling": True,
            "json_output": True,
            "multiple_system_messages": True,
            "structured_output": True,
            "vision": True,
        },
    )

    main_agent = AssistantAgent(
        name="main_agent",
        model_client=main_agent_model_client,
        tools=[tool],
        reflect_on_tool_use=True,
        description="An agent for testing",
    )
    result = await main_agent.run(task="Input task from user", cancellation_token=CancellationToken())
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Input task from user"
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], TextMessage)
    assert result.messages[2].content == "Input task from main agent"
    assert isinstance(result.messages[3], ToolCallRequestEvent)
    assert isinstance(result.messages[4], ToolCallExecutionEvent)
    assert isinstance(result.messages[5], TextMessage)
    assert result.messages[5].content == "Summary from tool agent"
    assert isinstance(result.messages[6], ToolCallExecutionEvent)
    assert isinstance(result.messages[7], TextMessage)
    assert result.messages[7].content == "Summary from main agent"


@pytest.mark.asyncio
async def test_team_tool_stream() -> None:
    """Test running a task with TeamTool in streaming mode."""
    agent1 = _EchoAgent("Agent1", "An agent for testing")
    agent2 = _EchoAgent("Agent2", "Another agent for testing")
    termination = MaxMessageTermination(max_messages=3)
    team = RoundRobinGroupChat(
        [agent1, agent2],
        termination_condition=termination,
    )
    tool = TeamTool(team=team, name="team_tool", description="A team tool for testing")

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                content=[FunctionCall(name="team_tool", arguments='{"task": "test task from main agent"}', id="1")],
                finish_reason="function_calls",
                usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
                cached=False,
            ),
            "Summary from main agent",
        ],
        model_info={
            "family": "gpt-41",
            "function_calling": True,
            "json_output": True,
            "multiple_system_messages": True,
            "structured_output": True,
            "vision": True,
        },
    )
    main_agent = AssistantAgent(
        name="main_agent",
        model_client=model_client,
        tools=[tool],
        reflect_on_tool_use=True,
        description="An agent for testing",
    )
    result = await main_agent.run(task="test task from user", cancellation_token=CancellationToken())
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "test task from user"
    assert isinstance(result.messages[1], ToolCallRequestEvent)
    assert isinstance(result.messages[2], TextMessage)
    assert result.messages[2].content == "test task from main agent"
    assert isinstance(result.messages[3], TextMessage)
    assert result.messages[3].content == "test task from main agent"
    assert result.messages[3].source == "Agent1"
    assert isinstance(result.messages[4], TextMessage)
    assert result.messages[4].content == "test task from main agent"
    assert result.messages[4].source == "Agent2"
    assert isinstance(result.messages[5], ToolCallExecutionEvent)
    assert isinstance(result.messages[6], TextMessage)
    assert result.messages[6].content == "Summary from main agent"
