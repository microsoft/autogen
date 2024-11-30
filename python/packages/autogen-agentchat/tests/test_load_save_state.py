import asyncio
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.state import (
    BaseGroupChatManagerState,
    MaxMessageTerminationState,
    TextMentionTerminationState,
)
from autogen_agentchat.task import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage


class _MockChatCompletion:
    def __init__(self, chat_completions: List[ChatCompletion]) -> None:
        self._saved_chat_completions = chat_completions
        self._curr_index = 0

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self._curr_index]
        self._curr_index += 1
        return completion


@pytest.fixture
def chat_completions() -> List[ChatCompletion]:
    """Fixture providing mock chat completions"""
    return [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="Test response 1", role="assistant"),
                )
            ],
            created=0,
            model="gpt-4o-2024-08-06",
            object="chat.completion",
            usage=CompletionUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="Test response 2", role="assistant"),
                )
            ],
            created=0,
            model="gpt-4o-2024-08-06",
            object="chat.completion",
            usage=CompletionUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15),
        ),
    ]


@pytest.fixture
def mock_chat_completion(monkeypatch: pytest.MonkeyPatch, chat_completions: List[ChatCompletion]) -> None:
    """Fixture that sets up the mock completion"""
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)


@pytest.mark.asyncio
async def test_max_message_termination_state() -> None:
    """Test saving and loading state for MaxMessageTermination"""
    term = MaxMessageTermination(max_messages=5)

    # Simulate some messages
    messages = [TextMessage(content="test", source="agent") for _ in range(3)]
    await term(messages)

    # Verify initial state through behavior
    assert not term.terminated  # Should not be terminated at 3 messages
    await term(messages)  # Send 3 more messages
    assert term.terminated  # Should be terminated now at 6 messages

    # Save state at 6 messages
    state = await term.save_state()
    assert isinstance(state, MaxMessageTerminationState)
    assert state.message_count == 6
    assert state.max_messages == 5

    # Load into new instance and verify behavior matches
    term2 = MaxMessageTermination(max_messages=10)  # Different max
    await term2.load_state(state)
    assert term2.terminated  # Should be terminated immediately since over max

    # Verify reset works
    await term2.reset()
    assert not term2.terminated
    # Single message
    await term2([TextMessage(content="test", source="agent")])
    assert not term2.terminated


@pytest.mark.asyncio
async def test_text_mention_termination_state() -> None:
    """Test saving and loading state for TextMentionTermination"""
    term = TextMentionTermination(text="STOP")

    # Test initial state
    assert not term.terminated
    await term([TextMessage(content="test STOP", source="agent")])
    assert term.terminated

    state = await term.save_state()
    assert isinstance(state, TextMentionTerminationState)
    assert state.terminated is True
    assert state.text == "STOP"

    # Load into new instance with different text
    term2 = TextMentionTermination(text="different")
    assert not term2.terminated
    await term2.load_state(state)
    assert term2.terminated

    # Verify reset works
    await term2.reset()
    assert not term2.terminated
    await term2([TextMessage(content="nothing special", source="agent")])
    assert not term2.terminated
    await term2([TextMessage(content="contains STOP word", source="agent")])
    assert term2.terminated


@pytest.mark.asyncio
async def test_team_state_validation(mock_chat_completion: None) -> None:
    """Test validation when loading team state with mismatched agents"""
    # Create agents with mocked client
    agent1 = AssistantAgent(
        name="agent1",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06", api_key="")
    )
    agent2 = AssistantAgent(
        name="agent2",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06", api_key="")
    )

    # Create and run initial team
    team = RoundRobinGroupChat([agent1], termination_condition=None)

    # Save the state
    state = await team.save_state()

    # Try loading into team with different agents
    team2 = RoundRobinGroupChat([agent1, agent2])
    with pytest.raises(ValueError) as exc:
        await team2.load_state(state)
    assert "Agent list mismatch".lower() in str(exc.value).lower()
    assert "missing" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_team_state_mocked(mock_chat_completion: None) -> None:
    # Create team with mocked agent
    assistant = AssistantAgent(
        name="assistant",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06", api_key="")
    )
    team = RoundRobinGroupChat(
        [assistant], termination_condition=MaxMessageTermination(max_messages=2))

    # Save state
    team_state = await team.save_state()

    # Verify state structure
    assert team_state.agent_names == ["assistant"]
    assert isinstance(team_state.termination_state, MaxMessageTerminationState)
    assert isinstance(team_state.manager_state, BaseGroupChatManagerState)

    # Create new team and load state
    team2 = RoundRobinGroupChat(
        [assistant], termination_condition=MaxMessageTermination(max_messages=2))
    await team2.load_state(team_state)

    # verify that team2 does indeed have the same state as team
    team2_state = await team2.save_state()
    assert team_state == team2_state
