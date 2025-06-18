from types import MethodType
from typing import Any, AsyncGenerator, List, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import AgentRuntime, SingleThreadedAgentRuntime
from autogen_core.models import CreateResult, LLMMessage, SystemMessage
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


@pytest.mark.asyncio
async def test_society_of_mind_agent_output_task_messages_parameter(runtime: AgentRuntime | None) -> None:
    """Test that output_task_messages parameter controls whether task messages are included in the stream."""
    model_client = ReplayChatCompletionClient(
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    )
    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(2)  # Reduce to 2 to use fewer responses
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)

    # Test 1: Test team with output_task_messages=True (default behavior)
    messages_with_task: List[BaseAgentEvent | BaseChatMessage] = []
    async for message in inner_team.run_stream(task="Count to 10", output_task_messages=True):
        if not isinstance(message, TaskResult):
            messages_with_task.append(message)

    # Should include the task message
    assert len(messages_with_task) >= 1
    assert any(
        isinstance(msg, TextMessage) and msg.source == "user" and "Count to 10" in msg.content
        for msg in messages_with_task
    )

    # Reset team before next test
    await inner_team.reset()

    # Test 2: Test team with output_task_messages=False
    messages_without_task: List[BaseAgentEvent | BaseChatMessage] = []
    async for message in inner_team.run_stream(task="Count to 10", output_task_messages=False):
        if not isinstance(message, TaskResult):
            messages_without_task.append(message)

    # Should NOT include the task message in the stream
    assert not any(
        isinstance(msg, TextMessage) and msg.source == "user" and "Count to 10" in msg.content
        for msg in messages_without_task
    )

    # Reset team before next test
    await inner_team.reset()

    # Test 3: Test SocietyOfMindAgent uses output_task_messages=False internally
    # Create a separate model client for SocietyOfMindAgent to ensure we have enough responses
    soma_model_client = ReplayChatCompletionClient(
        ["Final response from society of mind"],
    )
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=soma_model_client)

    # Collect all messages from the SocietyOfMindAgent stream
    soma_messages: List[BaseAgentEvent | BaseChatMessage] = []
    async for message in society_of_mind_agent.run_stream(task="Count to 10"):
        if not isinstance(message, TaskResult):
            soma_messages.append(message)

    # The SocietyOfMindAgent should output the task message (since it's the outer agent)
    # but should NOT forward the task messages from its inner team
    task_messages_in_soma = [msg for msg in soma_messages if isinstance(msg, TextMessage) and msg.source == "user"]

    # Count how many times "Count to 10" appears in the stream
    # With proper implementation, it should appear exactly once (from outer level only)
    count_task_messages = sum(
        1 for msg in soma_messages
        if isinstance(msg, TextMessage) and msg.source == "user" and "Count to 10" in msg.content
    )

    # Should have exactly one task message (from the outer level only)
    assert len(task_messages_in_soma) == 1
    assert count_task_messages == 1  # Should appear exactly once, not duplicated from inner team

    # Should have the SocietyOfMindAgent's final response
    soma_responses = [msg for msg in soma_messages if isinstance(msg, TextMessage) and msg.source == "society_of_mind"]
    assert len(soma_responses) == 1


@pytest.mark.asyncio
async def test_society_of_mind_agent_empty_messges(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    )
    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(3)
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)
    response = await society_of_mind_agent.run()
    assert len(response.messages) == 1
    assert response.messages[0].source == "society_of_mind"


@pytest.mark.asyncio
async def test_society_of_mind_agent_no_response(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["1", "2", "3"],
    )
    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(1)  # Set to 1 to force no response.
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client)
    response = await society_of_mind_agent.run(task="Count to 10.")
    assert len(response.messages) == 2
    assert response.messages[0].source == "user"
    assert response.messages[1].source == "society_of_mind"
    assert response.messages[1].to_text() == "No response."


@pytest.mark.asyncio
async def test_society_of_mind_agent_multiple_rounds(runtime: AgentRuntime | None) -> None:
    model_client = ReplayChatCompletionClient(
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
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

    # Continue.
    response = await society_of_mind_agent.run()
    assert len(response.messages) == 1
    assert response.messages[0].source == "society_of_mind"

    # Continue.
    response = await society_of_mind_agent.run()
    assert len(response.messages) == 1
    assert response.messages[0].source == "society_of_mind"


@pytest.mark.asyncio
async def test_society_of_mind_agent_no_multiple_system_messages(
    monkeypatch: pytest.MonkeyPatch, runtime: AgentRuntime | None
) -> None:
    model_client = ReplayChatCompletionClient(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])

    model_client_soma = ReplayChatCompletionClient(
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": False,
        },
    )

    original_create = model_client_soma.create

    # mock method with bound self
    async def _mock_create(
        self: ReplayChatCompletionClient, messages: Sequence[LLMMessage], *args: Any, **kwargs: Any
    ) -> CreateResult:
        for message in messages:
            assert not isinstance(message, SystemMessage)
        kwargs["messages"] = messages
        return await original_create(*args, **kwargs)

    # bind it
    monkeypatch.setattr(model_client_soma, "create", MethodType(_mock_create, model_client_soma))

    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(3)
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client_soma)
    await society_of_mind_agent.run(task="Count to 10.")


@pytest.mark.asyncio
async def test_society_of_mind_agent_yes_multiple_system_messages(
    monkeypatch: pytest.MonkeyPatch, runtime: AgentRuntime | None
) -> None:
    model_client = ReplayChatCompletionClient(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])

    model_client_soma = ReplayChatCompletionClient(
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
            "multiple_system_messages": True,
        },
    )

    original_create = model_client_soma.create

    # mock method with bound self
    async def _mock_create(
        self: ReplayChatCompletionClient, messages: Sequence[LLMMessage], *args: Any, **kwargs: Any
    ) -> CreateResult:
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[-1], SystemMessage)
        kwargs["messages"] = messages
        return await original_create(*args, **kwargs)

    # bind it
    monkeypatch.setattr(model_client_soma, "create", MethodType(_mock_create, model_client_soma))

    agent1 = AssistantAgent("assistant1", model_client=model_client, system_message="You are a helpful assistant.")
    agent2 = AssistantAgent("assistant2", model_client=model_client, system_message="You are a helpful assistant.")
    inner_termination = MaxMessageTermination(3)
    inner_team = RoundRobinGroupChat([agent1, agent2], termination_condition=inner_termination, runtime=runtime)
    society_of_mind_agent = SocietyOfMindAgent("society_of_mind", team=inner_team, model_client=model_client_soma)
    await society_of_mind_agent.run(task="Count to 10.")
