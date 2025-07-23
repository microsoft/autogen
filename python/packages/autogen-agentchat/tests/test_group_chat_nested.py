import logging
import tempfile
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    TextMessage,
)
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, Swarm
from autogen_core import AgentRuntime, SingleThreadedAgentRuntime
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.replay import ReplayChatCompletionClient

# Import test utilities from the main test file
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_group_chat_nested.log"))


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
async def test_round_robin_group_chat_nested_teams_run(runtime: AgentRuntime | None) -> None:
    """Test RoundRobinGroupChat with nested teams using run method."""
    model_client = ReplayChatCompletionClient(
        [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
            "Good job",
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        assistant = AssistantAgent(
            "assistant",
            model_client=model_client,
            description="An assistant agent that writes code.",
        )
        code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
        termination = TextMentionTermination("TERMINATE")

        # Create inner team (assistant + code executor)
        inner_team = RoundRobinGroupChat(
            participants=[assistant, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
        )

        # Create reviewer agent
        reviewer = AssistantAgent(
            "reviewer",
            model_client=model_client,
            description="A reviewer agent that reviews code.",
        )

        # Create outer team with nested inner team
        outer_team = RoundRobinGroupChat(
            participants=[inner_team, reviewer],
            termination_condition=termination,
            runtime=runtime,
        )

        result = await outer_team.run(task="Write a program that prints 'Hello, world!'")

        # Should have task message + inner team result + reviewer response + termination
        assert len(result.messages) >= 4
        assert isinstance(result.messages[0], TextMessage)
        assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
        assert result.stop_reason is not None and "TERMINATE" in result.stop_reason


@pytest.mark.asyncio
async def test_round_robin_group_chat_nested_teams_run_stream(runtime: AgentRuntime | None) -> None:
    """Test RoundRobinGroupChat with nested teams using run_stream method."""
    model_client = ReplayChatCompletionClient(
        [
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
            "Good job",
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        assistant = AssistantAgent(
            "assistant",
            model_client=model_client,
            description="An assistant agent that writes code.",
        )
        code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
        termination = TextMentionTermination("TERMINATE")

        # Create inner team (assistant + code executor)
        inner_team = RoundRobinGroupChat(
            participants=[assistant, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
        )

        # Create reviewer agent
        reviewer = AssistantAgent(
            "reviewer",
            model_client=model_client,
            description="A reviewer agent that reviews code.",
        )

        # Create outer team with nested inner team
        outer_team = RoundRobinGroupChat(
            participants=[inner_team, reviewer],
            termination_condition=termination,
            runtime=runtime,
        )

        messages: list[BaseAgentEvent | BaseChatMessage] = []
        result = None
        async for message in outer_team.run_stream(task="Write a program that prints 'Hello, world!'"):
            if isinstance(message, TaskResult):
                result = message
            else:
                messages.append(message)

        assert result is not None
        assert len(result.messages) >= 4
        assert isinstance(result.messages[0], TextMessage)
        assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
        assert result.stop_reason is not None and "TERMINATE" in result.stop_reason


@pytest.mark.asyncio
async def test_round_robin_group_chat_nested_teams_dump_load_component(runtime: AgentRuntime | None) -> None:
    """Test RoundRobinGroupChat with nested teams dump_component and load_component."""
    model_client = ReplayChatCompletionClient(["Hello from agent1", "Hello from agent2", "Hello from agent3"])

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    termination = MaxMessageTermination(2)

    # Create inner team
    inner_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
        name="InnerTeam",
        description="Inner team description",
    )

    # Create outer team with nested inner team
    outer_team = RoundRobinGroupChat(
        participants=[inner_team, agent3],
        termination_condition=termination,
        runtime=runtime,
        name="OuterTeam",
        description="Outer team description",
    )

    # Test dump_component
    config = outer_team.dump_component()
    assert config.config["name"] == "OuterTeam"
    assert config.config["description"] == "Outer team description"
    assert len(config.config["participants"]) == 2

    # First participant should be the inner team
    inner_team_config = config.config["participants"][0]["config"]
    assert inner_team_config["name"] == "InnerTeam"
    assert inner_team_config["description"] == "Inner team description"
    assert len(inner_team_config["participants"]) == 2

    # Second participant should be agent3
    agent3_config = config.config["participants"][1]["config"]
    assert agent3_config["name"] == "agent3"

    # Test load_component
    loaded_team = RoundRobinGroupChat.load_component(config)
    assert loaded_team.name == "OuterTeam"
    assert loaded_team.description == "Outer team description"
    assert len(loaded_team._participants) == 2  # type: ignore[reportPrivateUsage]

    # Verify the loaded team has the same structure
    loaded_config = loaded_team.dump_component()
    assert loaded_config == config


@pytest.mark.asyncio
async def test_round_robin_group_chat_nested_teams_save_load_state(runtime: AgentRuntime | None) -> None:
    """Test RoundRobinGroupChat with nested teams save_state and load_state."""
    model_client = ReplayChatCompletionClient(["Hello from agent1", "Hello from agent2", "TERMINATE"])

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    termination = TextMentionTermination("TERMINATE")  # Use TextMentionTermination

    # Create inner team
    inner_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
    )

    # Create outer team with nested inner team
    outer_team1 = RoundRobinGroupChat(
        participants=[inner_team, agent3],
        termination_condition=termination,
        runtime=runtime,
    )

    # Run the team to generate state
    await outer_team1.run(task="Test message")

    # Save state
    state = await outer_team1.save_state()

    # Create new agents and teams
    agent4 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent5 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent6 = AssistantAgent("agent3", model_client=model_client, description="Third agent")

    inner_team2 = RoundRobinGroupChat(
        participants=[agent4, agent5],
        termination_condition=termination,
        runtime=runtime,
    )

    outer_team2 = RoundRobinGroupChat(
        participants=[inner_team2, agent6],
        termination_condition=termination,
        runtime=runtime,
    )

    # Load state
    await outer_team2.load_state(state)

    # Verify state was loaded correctly
    state2 = await outer_team2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_selector_group_chat_nested_teams_run(runtime: AgentRuntime | None) -> None:
    """Test SelectorGroupChat with nested teams using run method."""
    model_client = ReplayChatCompletionClient(
        [
            "InnerTeam",  # Select inner team first
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
            "agent3",  # Select agent3 (reviewer)
            "Good job",
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        assistant = AssistantAgent(
            "assistant",
            model_client=model_client,
            description="An assistant agent that writes code.",
        )
        code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
        termination = TextMentionTermination("TERMINATE")

        # Create inner team (assistant + code executor)
        inner_team = RoundRobinGroupChat(
            participants=[assistant, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
            name="InnerTeam",
            description="Team that writes and executes code",
        )

        # Create reviewer agent
        reviewer = AssistantAgent(
            "agent3",
            model_client=model_client,
            description="A reviewer agent that reviews code.",
        )

        # Create outer team with nested inner team
        outer_team = SelectorGroupChat(
            participants=[inner_team, reviewer],
            model_client=model_client,
            termination_condition=termination,
            runtime=runtime,
        )

        result = await outer_team.run(task="Write a program that prints 'Hello, world!'")

        # Should have task message + selector events + inner team result + reviewer response
        assert len(result.messages) >= 4
        assert isinstance(result.messages[0], TextMessage)
        assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
        assert result.stop_reason is not None and "TERMINATE" in result.stop_reason


@pytest.mark.asyncio
async def test_selector_group_chat_nested_teams_run_stream(runtime: AgentRuntime | None) -> None:
    """Test SelectorGroupChat with nested teams using run_stream method."""
    model_client = ReplayChatCompletionClient(
        [
            "InnerTeam",  # Select inner team first
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "TERMINATE",
            "agent3",  # Select agent3 (reviewer)
            "Good job",
            "TERMINATE",
        ],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor = LocalCommandLineCodeExecutor(work_dir=temp_dir)
        assistant = AssistantAgent(
            "assistant",
            model_client=model_client,
            description="An assistant agent that writes code.",
        )
        code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
        termination = TextMentionTermination("TERMINATE")

        # Create inner team (assistant + code executor)
        inner_team = RoundRobinGroupChat(
            participants=[assistant, code_executor_agent],
            termination_condition=termination,
            runtime=runtime,
            name="InnerTeam",
            description="Team that writes and executes code",
        )

        # Create reviewer agent
        reviewer = AssistantAgent(
            "agent3",
            model_client=model_client,
            description="A reviewer agent that reviews code.",
        )

        # Create outer team with nested inner team
        outer_team = SelectorGroupChat(
            participants=[inner_team, reviewer],
            model_client=model_client,
            termination_condition=termination,
            runtime=runtime,
        )

        messages: list[BaseAgentEvent | BaseChatMessage] = []
        result = None
        async for message in outer_team.run_stream(task="Write a program that prints 'Hello, world!'"):
            if isinstance(message, TaskResult):
                result = message
            else:
                messages.append(message)

        assert result is not None
        assert len(result.messages) >= 4
        assert isinstance(result.messages[0], TextMessage)
        assert result.messages[0].content == "Write a program that prints 'Hello, world!'"
        assert result.stop_reason is not None and "TERMINATE" in result.stop_reason


@pytest.mark.asyncio
async def test_selector_group_chat_nested_teams_dump_load_component(runtime: AgentRuntime | None) -> None:
    """Test SelectorGroupChat with nested teams dump_component and load_component."""
    model_client = ReplayChatCompletionClient(["agent1", "Hello from agent1", "agent3", "Hello from agent3"])

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    termination = MaxMessageTermination(2)

    # Create inner team
    inner_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
        name="InnerTeam",
        description="Inner team description",
    )

    # Create outer team with nested inner team
    outer_team = SelectorGroupChat(
        participants=[inner_team, agent3],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
        name="OuterTeam",
        description="Outer team description",
    )

    # Test dump_component
    config = outer_team.dump_component()
    assert config.config["name"] == "OuterTeam"
    assert config.config["description"] == "Outer team description"
    assert len(config.config["participants"]) == 2

    # First participant should be the inner team
    inner_team_config = config.config["participants"][0]["config"]
    assert inner_team_config["name"] == "InnerTeam"
    assert inner_team_config["description"] == "Inner team description"
    assert len(inner_team_config["participants"]) == 2

    # Second participant should be agent3
    agent3_config = config.config["participants"][1]["config"]
    assert agent3_config["name"] == "agent3"

    # Test load_component
    loaded_team = SelectorGroupChat.load_component(config)
    assert loaded_team.name == "OuterTeam"
    assert loaded_team.description == "Outer team description"
    assert len(loaded_team._participants) == 2  # type: ignore[reportPrivateUsage]

    # Verify the loaded team has the same structure
    loaded_config = loaded_team.dump_component()
    assert loaded_config == config


@pytest.mark.asyncio
async def test_selector_group_chat_nested_teams_save_load_state(runtime: AgentRuntime | None) -> None:
    """Test SelectorGroupChat with nested teams save_state and load_state."""
    model_client = ReplayChatCompletionClient(["InnerTeam", "Hello from inner team", "agent3", "TERMINATE"])

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    termination = TextMentionTermination("TERMINATE")

    # Create inner team
    inner_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
        runtime=runtime,
        name="InnerTeam",
    )

    # Create outer team with nested inner team
    outer_team1 = SelectorGroupChat(
        participants=[inner_team, agent3],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
    )

    # Run the team to generate state
    await outer_team1.run(task="Test message")

    # Save state
    state = await outer_team1.save_state()

    # Create new agents and teams
    agent4 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent5 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent6 = AssistantAgent("agent3", model_client=model_client, description="Third agent")

    inner_team2 = RoundRobinGroupChat(
        participants=[agent4, agent5],
        termination_condition=termination,
        runtime=runtime,
        name="InnerTeam",
    )

    outer_team2 = SelectorGroupChat(
        participants=[inner_team2, agent6],
        model_client=model_client,
        termination_condition=termination,
        runtime=runtime,
    )

    # Load state
    await outer_team2.load_state(state)

    # Verify state was loaded correctly
    state2 = await outer_team2.save_state()
    assert state == state2


@pytest.mark.asyncio
async def test_swarm_doesnt_support_nested_teams() -> None:
    """Test that Swarm raises TypeError when provided with nested teams."""
    model_client = ReplayChatCompletionClient(["Hello", "TERMINATE"])

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    termination = TextMentionTermination("TERMINATE")

    # Create inner team
    inner_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=termination,
    )

    # Verify that Swarm raises TypeError when trying to use a team as participant
    with pytest.raises(TypeError, match="Participant .* must be a ChatAgent"):
        Swarm(
            participants=[inner_team, agent3],  # type: ignore
            termination_condition=termination,
        )


@pytest.mark.asyncio
async def test_round_robin_deeply_nested_teams(runtime: AgentRuntime | None) -> None:
    """Test RoundRobinGroupChat with deeply nested teams (3 levels)."""
    model_client = ReplayChatCompletionClient(
        [
            "Hello from agent1",
            "TERMINATE from agent2",
            "World from agent3",
            "Hello from agent1",
            "Hello from agent2",
            "TERMINATE from agent1",
            "TERMINATE from agent3",
            "Review from agent4",
            "TERMINATE from agent2",
            "TERMINATE from agent3",
            "TERMINATE from agent4",
        ]
    )

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client, description="Third agent")
    agent4 = AssistantAgent("agent4", model_client=model_client, description="Fourth agent")

    # Create innermost team (level 1)
    innermost_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent1", "agent2"]),
        runtime=runtime,
        name="InnermostTeam",
    )

    # Create middle team (level 2)
    middle_team = RoundRobinGroupChat(
        participants=[innermost_team, agent3],
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent3"]),
        runtime=runtime,
        name="MiddleTeam",
    )

    # Create outermost team (level 3)
    outermost_team = RoundRobinGroupChat(
        participants=[middle_team, agent4],
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent4"]),
        runtime=runtime,
        name="OutermostTeam",
    )

    result: TaskResult | None = None
    async for msg in outermost_team.run_stream(task="Test deep nesting"):
        if isinstance(msg, TaskResult):
            result = msg
    assert result is not None
    # Should have task message + responses from each level
    assert len(result.messages) == 12
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Test deep nesting"
    assert result.stop_reason is not None and "TERMINATE" in result.stop_reason

    # Test component serialization of deeply nested structure
    config = outermost_team.dump_component()
    loaded_team = RoundRobinGroupChat.load_component(config)
    assert loaded_team.name == "OutermostTeam"

    # Verify nested structure is preserved
    loaded_config = loaded_team.dump_component()
    assert loaded_config == config


@pytest.mark.asyncio
async def test_selector_deeply_nested_teams(runtime: AgentRuntime | None) -> None:
    """Test SelectorGroupChat with deeply nested teams (3 levels)."""
    model_client_inner = ReplayChatCompletionClient(
        [
            "Hello from innermost agent 1",
            "Hello from innermost agent 2",
            "TERMINATE from innermost agent 1",
        ]
    )
    model_client_middle = ReplayChatCompletionClient(
        [
            "InnermostTeam",  # Select innermost team
            "TERMINATE from agent3",
        ]
    )
    model_client_outter = ReplayChatCompletionClient(
        [
            "MiddleTeam",  # Select middle team
            "agent4",  # Select agent4
            "Hello from outermost agent 4",
            "agent4",  # Select agent4 again
            "TERMINATE from agent4",
        ]
    )

    # Create agents
    agent1 = AssistantAgent("agent1", model_client=model_client_inner, description="First agent")
    agent2 = AssistantAgent("agent2", model_client=model_client_inner, description="Second agent")
    agent3 = AssistantAgent("agent3", model_client=model_client_middle, description="Third agent")
    agent4 = AssistantAgent("agent4", model_client=model_client_outter, description="Fourth agent")

    # Create innermost team (level 1) - RoundRobin for simplicity
    innermost_team = RoundRobinGroupChat(
        participants=[agent1, agent2],
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent1", "agent2"]),
        runtime=runtime,
        name="InnermostTeam",
    )

    # Create middle team (level 2) - Selector
    middle_team = SelectorGroupChat(
        participants=[innermost_team, agent3],
        model_client=model_client_middle,
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent3"]),
        runtime=runtime,
        name="MiddleTeam",
    )

    # Create outermost team (level 3) - Selector
    outermost_team = SelectorGroupChat(
        participants=[middle_team, agent4],
        model_client=model_client_outter,
        termination_condition=TextMentionTermination("TERMINATE", sources=["agent4"]),
        runtime=runtime,
        name="OutermostTeam",
        allow_repeated_speaker=True,
    )

    result: TaskResult | None = None
    async for msg in outermost_team.run_stream(task="Test deep nesting"):
        if isinstance(msg, TaskResult):
            result = msg
    assert result is not None

    # Should have task message + selector events + responses from each level
    assert len(result.messages) == 7
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].content == "Test deep nesting"
    assert result.stop_reason is not None and "TERMINATE" in result.stop_reason

    # Test component serialization of deeply nested structure
    config = outermost_team.dump_component()
    loaded_team = SelectorGroupChat.load_component(config)
    assert loaded_team.name == "OutermostTeam"

    # Verify nested structure is preserved
    loaded_config = loaded_team.dump_component()
    assert loaded_config == config
