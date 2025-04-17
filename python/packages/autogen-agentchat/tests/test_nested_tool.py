import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import AgentChatRuntimeContext
from autogen_agentchat.teams._group_chat._base_group_chat import BaseGroupChat
from autogen_agentchat.teams._group_chat._events import GroupChatMessage
from autogen_core import (
    CancellationToken,
    ClosureAgent,
    ClosureContext,
    ComponentModel,
    DefaultSubscription,
    DefaultTopicId,
    MessageContext,
    SingleThreadedAgentRuntime,
)
from autogen_ext.tools.nested import AgentTool, TeamTool
from autogen_ext.tools.nested._agent import AgentToolState
from autogen_ext.tools.nested._task_runner_tool import TaskRunnerToolInput
from autogen_ext.tools.nested._team import TeamToolState


class MockTaskRunner:
    """Mock task runner for testing."""

    def __init__(self, messages=None):
        self.messages = messages or [TextMessage(content="Task completed successfully", source="test_source")]

        # Create a component model for dump_component
        mock_component = MagicMock(spec=ComponentModel)
        mock_component.provider = "mock_provider"
        mock_component.config = {"type": "mock_task_runner"}
        self.component_model = mock_component

    async def run_stream(self, task, cancellation_token):
        """Implement an async generator that can be used with 'async for'."""

        # Yield each message
        for message in self.messages:
            yield message

        # Finally yield the TaskResult
        yield TaskResult(messages=self.messages)

    async def save_state(self):
        return {"state": "saved"}

    def dump_component(self):
        return self.component_model


@pytest.fixture
def mock_group_chat():
    """Create a mock group chat that implements BaseGroupChat."""
    mock = MagicMock(spec=BaseGroupChat)
    task_runner = MockTaskRunner()

    # Add all the methods from MockTaskRunner to the mock
    mock.run_stream = task_runner.run_stream
    mock.save_state = task_runner.save_state
    mock.dump_component = task_runner.dump_component

    # Add tracking properties
    mock.component_model = task_runner.component_model

    # Add name and description for TeamTool
    mock.name = "Mock Group Chat"
    mock.description = "A mock group chat for testing"

    return mock


@pytest.fixture
def mock_chat_agent():
    """Create a mock chat agent that implements BaseChatAgent."""
    mock = MagicMock(spec=BaseChatAgent)
    task_runner = MockTaskRunner()

    # Add all the methods from MockTaskRunner to the mock
    mock.run_stream = task_runner.run_stream
    mock.save_state = task_runner.save_state
    mock.dump_component = task_runner.dump_component

    # Add tracking properties
    mock.component_model = task_runner.component_model

    # Add name and description for AgentTool
    mock.name = "Mock Agent"
    mock.description = "A mock agent for testing"

    return mock


# Tests for AgentTool
@pytest.mark.asyncio
async def test_agent_tool_init(mock_chat_agent):
    """Test initialization of AgentTool."""
    tool = AgentTool(agent=mock_chat_agent)

    assert tool.name == "Mock Agent"
    assert tool.description == "A mock agent for testing"
    assert tool._agent == mock_chat_agent
    assert tool._task_runner == mock_chat_agent


@pytest.mark.asyncio
async def test_agent_tool_run(mock_chat_agent):
    """Test running a task with AgentTool."""
    tool = AgentTool(agent=mock_chat_agent)
    queue = asyncio.Queue[GroupChatMessage]()

    async def output_result(_ctx: ClosureContext, message: GroupChatMessage, ctx: MessageContext) -> None:
        print(f"Received message: {message}")
        await queue.put(message)

    runtime = SingleThreadedAgentRuntime()
    await ClosureAgent.register_closure(
        runtime, "test_output_topic", output_result, subscriptions=lambda: [DefaultSubscription()]
    )
    runtime.start()

    with AgentChatRuntimeContext.populate_context((runtime, DefaultTopicId())):
        result = await tool.run(args=TaskRunnerToolInput(task="Test task"), cancellation_token=CancellationToken())

    await runtime.stop_when_idle()
    assert queue.qsize() == 1

    message = await queue.get()
    assert message.message.content == "Task completed successfully"

    # Verify the result is a JSON string of TaskResult
    task_result = json.loads(result)
    assert "messages" in task_result
    assert task_result["messages"][0]["content"] == "Task completed successfully"


@pytest.mark.asyncio
async def test_agent_tool_run_without_runtime_context():
    """Test running a task without a runtime context raises an error."""
    tool = AgentTool(agent=MagicMock(spec=BaseChatAgent))

    # No runtime context available should raise an error
    with pytest.raises(RuntimeError, match="TaskRunnerTool must be used within an AgentChatRuntimeContext"):
        await tool.run(args=TaskRunnerToolInput(task="Test task"), cancellation_token=CancellationToken())


@pytest.mark.asyncio
async def test_agent_tool_save_state(mock_chat_agent):
    """Test saving state of AgentTool."""
    tool = AgentTool(agent=mock_chat_agent)

    state = await tool.save_state()

    # Verify the state is correct
    assert isinstance(state, AgentToolState)
    assert state.agent_state == {"state": "saved"}


def test_agent_tool_to_config(mock_chat_agent):
    """Test serialization of AgentTool to config."""
    tool = AgentTool(agent=mock_chat_agent)

    config = tool._to_config()

    # Verify the config is correct
    assert config.agent.provider == "mock_provider"
    assert config.agent.config == {"type": "mock_task_runner"}


@pytest.mark.asyncio
async def test_agent_tool_from_config():
    """Test deserialization of AgentTool from config."""
    # Create a mock component loader that returns our mock agent
    mock_agent = MagicMock(spec=BaseChatAgent)
    mock_agent.name = "Loaded Agent"
    mock_agent.description = "A loaded agent for testing"

    with patch("autogen_ext.tools.nested._agent.BaseChatAgent") as mock_agent_class:
        mock_agent_class.load_component.return_value = mock_agent

        config = MagicMock()
        config.agent = MagicMock()

        agent_tool = AgentTool._from_config(config)

    # Verify the deserialized tool has the correct properties
    assert isinstance(agent_tool, AgentTool)
    assert agent_tool._agent == mock_agent
    assert agent_tool.name == "Loaded Agent"
    assert agent_tool.description == "A loaded agent for testing"


# Tests for TeamTool
@pytest.mark.asyncio
async def test_team_tool_init(mock_group_chat):
    """Test initialization of TeamTool."""
    tool = TeamTool(team=mock_group_chat, name="Team Tool", description="A team tool for testing")

    assert tool.name == "Team Tool"
    assert tool.description == "A team tool for testing"
    assert tool._team == mock_group_chat
    assert tool._task_runner == mock_group_chat


@pytest.mark.asyncio
async def test_team_tool_run(mock_group_chat):
    """Test running a task with TeamTool."""
    tool = TeamTool(team=mock_group_chat, name="Team Tool", description="A team tool for testing")
    queue = asyncio.Queue[GroupChatMessage]()

    async def output_result(_ctx: ClosureContext, message: GroupChatMessage, ctx: MessageContext) -> None:
        print(f"Received message: {message}")
        await queue.put(message)

    runtime = SingleThreadedAgentRuntime()
    await ClosureAgent.register_closure(
        runtime, "test_output_topic", output_result, subscriptions=lambda: [DefaultSubscription()]
    )
    runtime.start()

    with AgentChatRuntimeContext.populate_context((runtime, DefaultTopicId())):
        result = await tool.run(args=TaskRunnerToolInput(task="Test task"), cancellation_token=CancellationToken())

    await runtime.stop_when_idle()
    assert queue.qsize() == 1

    message = await queue.get()
    assert message.message.content == "Task completed successfully"

    # Verify the result is a JSON string of TaskResult
    task_result = json.loads(result)
    assert "messages" in task_result
    assert task_result["messages"][0]["content"] == "Task completed successfully"


@pytest.mark.asyncio
async def test_team_tool_run_without_runtime_context():
    """Test running a task without a runtime context raises an error."""
    tool = TeamTool(team=MagicMock(spec=BaseGroupChat), name="Team Tool", description="A team tool for testing")

    # No runtime context available should raise an error
    with pytest.raises(RuntimeError, match="TaskRunnerTool must be used within an AgentChatRuntimeContext"):
        await tool.run(args=TaskRunnerToolInput(task="Test task"), cancellation_token=CancellationToken())


@pytest.mark.asyncio
async def test_team_tool_save_state(mock_group_chat):
    """Test saving state of TeamTool."""
    tool = TeamTool(team=mock_group_chat, name="Team Tool", description="A team tool for testing")

    state = await tool.save_state()

    # Verify the state is correct
    assert isinstance(state, TeamToolState)
    assert state.team_state == {"state": "saved"}


def test_team_tool_to_config(mock_group_chat):
    """Test serialization of TeamTool to config."""
    tool = TeamTool(team=mock_group_chat, name="Team Tool", description="A team tool for testing")

    config = tool._to_config()

    # Verify the config is correct
    assert config.name == "Team Tool"
    assert config.description == "A team tool for testing"
    assert config.team.provider == "mock_provider"
    assert config.team.config == {"type": "mock_task_runner"}


@pytest.mark.asyncio
async def test_team_tool_from_config():
    """Test deserialization of TeamTool from config."""
    # Create a mock component loader that returns our mock team
    mock_team = MagicMock(spec=BaseGroupChat)

    with patch("autogen_ext.tools.nested._team.BaseGroupChat") as mock_team_class:
        mock_team_class.load_component.return_value = mock_team

        config = MagicMock()
        config.name = "Loaded Team Tool"
        config.description = "A loaded team tool for testing"
        config.team = MagicMock()

        team_tool = TeamTool._from_config(config)

    # Verify the deserialized tool has the correct properties
    assert isinstance(team_tool, TeamTool)
    assert team_tool._team == mock_team
    assert team_tool.name == "Loaded Team Tool"
    assert team_tool.description == "A loaded team tool for testing"
