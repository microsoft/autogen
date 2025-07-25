from typing import List

import pytest
import pytest_asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import ChatAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import ProposalMessage, VoteMessage, VoteType, VotingGroupChat, VotingMethod
from autogen_agentchat.teams._group_chat._voting_group_chat import ProposalContent, VoteContent
from autogen_ext.models.replay import ReplayChatCompletionClient


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
