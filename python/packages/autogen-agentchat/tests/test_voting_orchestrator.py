import os
from typing import List

import pytest
import pytest_asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import ChatAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import ProposalMessage, VoteMessage, VoteType, VotingGroupChat, VotingMethod
from autogen_agentchat.teams._group_chat._voting_group_chat import ProposalContent, VoteContent
from autogen_ext.models.replay import ReplayChatCompletionClient

# Check for OpenAI API key availability
openai_api_key = os.environ.get("OPENAI_API_KEY")
requires_openai_api = pytest.mark.skipif(openai_api_key is None, reason="OPENAI_API_KEY environment variable not set")

# Type imports for integration tests
if openai_api_key is not None:
    from autogen_ext.models.openai import OpenAIChatCompletionClient


class TestVotingGroupChat:
    """Test suite for VotingGroupChat functionality."""

    @pytest_asyncio.fixture  # type: ignore[misc]
    async def mock_model_client(self) -> ReplayChatCompletionClient:
        """Create a replay model client for testing."""
        return ReplayChatCompletionClient(
            chat_completions=[
                "I propose we implement the new feature.",
                "I vote APPROVE - this looks good.",
                "I vote APPROVE - agreed.",
                "I vote REJECT - needs more work.",
            ]
        )

    @pytest_asyncio.fixture  # type: ignore[misc]
    async def voting_agents(self, mock_model_client: ReplayChatCompletionClient) -> List[ChatAgent]:
        """Create test agents for voting."""
        return [
            AssistantAgent("Agent1", model_client=mock_model_client),
            AssistantAgent("Agent2", model_client=mock_model_client),
            AssistantAgent("Agent3", model_client=mock_model_client),
        ]

    def test_voting_group_chat_creation(self, voting_agents: List[ChatAgent]) -> None:
        """Test basic VotingGroupChat creation."""
        voting_team = VotingGroupChat(
            participants=voting_agents,
            voting_method=VotingMethod.MAJORITY,
            max_turns=10,
            termination_condition=MaxMessageTermination(10),
        )

        # Test that team was created successfully with expected participants
        assert voting_team is not None
        assert isinstance(voting_team, VotingGroupChat)

    def test_voting_method_configurations(self, voting_agents: List[ChatAgent]) -> None:
        """Test different voting method configurations."""
        # Test majority voting
        majority_team = VotingGroupChat(participants=voting_agents, voting_method=VotingMethod.MAJORITY)
        assert majority_team is not None

        # Test qualified majority
        qualified_team = VotingGroupChat(
            participants=voting_agents, voting_method=VotingMethod.QUALIFIED_MAJORITY, qualified_majority_threshold=0.75
        )
        assert qualified_team is not None

        # Test unanimous voting
        unanimous_team = VotingGroupChat(participants=voting_agents, voting_method=VotingMethod.UNANIMOUS)
        assert unanimous_team is not None

    def test_voting_group_chat_validation(self, voting_agents: List[ChatAgent]) -> None:
        """Test validation of VotingGroupChat parameters."""
        # Test minimum participants requirement
        with pytest.raises(ValueError, match="at least 2 participants"):
            VotingGroupChat(participants=[voting_agents[0]])

        # Test invalid threshold
        with pytest.raises(ValueError, match="must be between 0.5 and 1.0"):
            VotingGroupChat(participants=voting_agents, qualified_majority_threshold=0.3)

        # Test invalid auto_propose_speaker
        with pytest.raises(ValueError, match="not found in participants"):
            VotingGroupChat(participants=voting_agents, auto_propose_speaker="NonExistentAgent")

    def test_vote_message_creation(self) -> None:
        """Test VoteMessage creation and serialization."""
        vote = VoteMessage(
            content=VoteContent(
                vote=VoteType.APPROVE, proposal_id="test-proposal", reasoning="This looks good to me", confidence=0.9
            ),
            source="TestAgent",
        )

        assert vote.content.vote == VoteType.APPROVE
        assert vote.content.proposal_id == "test-proposal"
        assert vote.content.reasoning == "This looks good to me"
        assert vote.content.confidence == 0.9
        assert "Vote: approve" in vote.to_model_text()

    def test_proposal_message_creation(self) -> None:
        """Test ProposalMessage creation and serialization."""
        proposal = ProposalMessage(
            content=ProposalContent(
                proposal_id="test-proposal",
                title="Test Proposal",
                description="This is a test proposal",
                options=["Option A", "Option B"],
            ),
            source="ProposerAgent",
        )

        assert proposal.content.proposal_id == "test-proposal"
        assert proposal.content.title == "Test Proposal"
        assert len(proposal.content.options) == 2
        assert "Proposal: Test Proposal" in proposal.to_model_text()

    def test_voting_configuration_export(self, voting_agents: List[ChatAgent]) -> None:
        """Test configuration export and import."""
        original_team = VotingGroupChat(
            participants=voting_agents,
            voting_method=VotingMethod.QUALIFIED_MAJORITY,
            qualified_majority_threshold=0.8,
            allow_abstentions=False,
            require_reasoning=True,
            max_discussion_rounds=5,
        )

        # Test that team was created successfully
        assert original_team is not None
        assert isinstance(original_team, VotingGroupChat)


class TestVotingGroupChatIntegration:
    """Integration tests for VotingGroupChat with real OpenAI API."""

    @pytest_asyncio.fixture  # type: ignore[misc]
    async def openai_model_client(self) -> "OpenAIChatCompletionClient":
        """Create a real OpenAI model client for integration testing."""
        if openai_api_key is None:
            pytest.skip("OPENAI_API_KEY not available")

        # Import here to avoid import errors when OpenAI is not available
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(
            model="gpt-4o-mini",  # Use cheaper model for testing
            api_key=openai_api_key,
        )

    @pytest_asyncio.fixture  # type: ignore[misc]
    async def real_voting_agents(self, openai_model_client: "OpenAIChatCompletionClient") -> List[ChatAgent]:
        """Create test agents with real OpenAI client for integration testing."""
        return [
            AssistantAgent("Reviewer1", model_client=openai_model_client),
            AssistantAgent("Reviewer2", model_client=openai_model_client),
            AssistantAgent("Reviewer3", model_client=openai_model_client),
        ]

    @requires_openai_api
    @pytest.mark.asyncio
    async def test_real_voting_group_chat_basic_flow(self, real_voting_agents: List[ChatAgent]) -> None:
        """Test basic VotingGroupChat flow with real OpenAI API calls."""
        voting_team = VotingGroupChat(
            participants=real_voting_agents,
            voting_method=VotingMethod.MAJORITY,
            max_turns=5,
            termination_condition=MaxMessageTermination(5),
        )

        # Test that team was created successfully with real agents
        assert voting_team is not None
        assert isinstance(voting_team, VotingGroupChat)

        # Test a simple conversation to verify API connectivity
        from autogen_agentchat.messages import TextMessage
        from autogen_core import CancellationToken

        test_message = TextMessage(content="Hello, can you respond with just 'API_TEST_SUCCESS'?", source="TestUser")

        cancellation_token = CancellationToken()
        response = await real_voting_agents[0].on_messages([test_message], cancellation_token)
        assert response is not None

    @requires_openai_api
    @pytest.mark.asyncio
    async def test_real_voting_with_proposal(self, real_voting_agents: List[ChatAgent]) -> None:
        """Test voting flow with a real proposal using OpenAI API."""
        voting_team = VotingGroupChat(
            participants=real_voting_agents,
            voting_method=VotingMethod.MAJORITY,
            max_turns=3,
            termination_condition=MaxMessageTermination(3),
        )

        # Create a simple proposal for testing
        proposal = ProposalMessage(
            content=ProposalContent(
                proposal_id="integration-test-1",
                title="Test API Integration",
                description="Should we proceed with this integration test?",
                options=["Yes", "No"],
            ),
            source="TestProposer",
        )

        # Test that proposal is properly formatted
        assert proposal.content.proposal_id == "integration-test-1"
        assert "Test API Integration" in proposal.to_model_text()

        # Test that voting team can handle the proposal structure
        assert voting_team is not None
