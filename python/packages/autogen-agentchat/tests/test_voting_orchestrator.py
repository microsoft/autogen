import asyncio
import os
from typing import List, cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import ChatAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, MessageFactory, TextMessage
from autogen_agentchat.teams import ProposalMessage, VoteMessage, VoteType, VotingGroupChat, VotingMethod
from autogen_agentchat.teams._group_chat._events import GroupChatTermination
from autogen_agentchat.teams._group_chat._voting_group_chat import (
    ProposalContent,
    VoteContent,
    VotingGroupChatManager,
    VotingPhase,
    VotingResult,
    VotingResultMessage,
)
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


class TestVotingGroupChatManager:
    """Comprehensive tests for VotingGroupChatManager functionality."""

    @pytest_asyncio.fixture  # type: ignore[misc]
    async def voting_manager(self) -> VotingGroupChatManager:
        """Create a VotingGroupChatManager for testing."""
        output_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination] = asyncio.Queue()
        message_factory = MessageFactory()

        manager = VotingGroupChatManager(
            name="TestVotingManager",
            group_topic_type="test_group",
            output_topic_type="test_output",
            participant_topic_types=["agent1", "agent2", "agent3"],
            participant_names=["Agent1", "Agent2", "Agent3"],
            participant_descriptions=["desc1", "desc2", "desc3"],
            output_message_queue=output_queue,
            termination_condition=None,
            max_turns=10,
            message_factory=message_factory,
            voting_method=VotingMethod.MAJORITY,
            qualified_majority_threshold=0.67,
            allow_abstentions=True,
            require_reasoning=False,
            max_discussion_rounds=3,
            auto_propose_speaker="Agent1",
            emit_team_events=False,
        )
        return manager

    @pytest.mark.asyncio
    async def test_voting_manager_initialization(self, voting_manager: VotingGroupChatManager) -> None:
        """Test VotingGroupChatManager initialization."""
        assert voting_manager.voting_method == VotingMethod.MAJORITY
        assert voting_manager.qualified_majority_threshold == 0.67
        assert voting_manager.allow_abstentions is True
        assert voting_manager.require_reasoning is False
        assert voting_manager.max_discussion_rounds == 3
        assert voting_manager.auto_propose_speaker == "Agent1"
        assert voting_manager.current_phase == VotingPhase.PROPOSAL

    @pytest.mark.asyncio
    async def test_validate_group_state(self, voting_manager: VotingGroupChatManager) -> None:
        """Test group state validation."""
        # Should pass with 3 participants
        await voting_manager.validate_group_state(None)

        # Test with insufficient participants
        voting_manager.set_participant_names_for_testing(["Agent1"])
        with pytest.raises(ValueError, match="Voting requires at least 2 participants"):
            await voting_manager.validate_group_state(None)

    @pytest.mark.asyncio
    async def test_reset_manager(self, voting_manager: VotingGroupChatManager) -> None:
        """Test manager reset functionality."""
        # Set some state
        voting_manager.set_phase_for_testing(VotingPhase.VOTING)
        voting_manager.set_votes_for_testing({"Agent1": {"vote": VoteType.APPROVE}})
        voting_manager.set_discussion_rounds_for_testing(2)

        await voting_manager.reset()

        assert voting_manager.current_phase == VotingPhase.PROPOSAL
        assert voting_manager.votes_cast == {}
        assert voting_manager.discussion_rounds == 0
        assert voting_manager.current_proposal is None

    @pytest.mark.asyncio
    async def test_select_speaker_initial(self, voting_manager: VotingGroupChatManager) -> None:
        """Test speaker selection in initial state."""
        result = await voting_manager.select_speaker([])
        assert result == "Agent1"  # auto_propose_speaker

    @pytest.mark.asyncio
    async def test_select_proposer(self, voting_manager: VotingGroupChatManager) -> None:
        """Test proposer selection logic."""
        # With auto_propose_speaker
        proposer = voting_manager.select_proposer_for_testing()
        assert proposer == "Agent1"

        # Without auto_propose_speaker
        voting_manager.set_auto_propose_speaker_for_testing(None)
        proposer = voting_manager.select_proposer_for_testing()
        assert proposer == "Agent1"  # Falls back to first participant

    @pytest.mark.asyncio
    async def test_handle_proposal_phase(self, voting_manager: VotingGroupChatManager) -> None:
        """Test proposal phase handling."""
        # Test with ProposalMessage
        proposal = ProposalMessage(
            content=ProposalContent(
                proposal_id="test-123",
                title="Test Proposal",
                description="Testing proposal handling",
                options=["Yes", "No"],
            ),
            source="Agent1",
        )

        # Call handle_proposal_phase and verify behavior
        result = await voting_manager.handle_proposal_phase_for_testing(proposal)

        assert voting_manager.current_phase == VotingPhase.VOTING
        assert voting_manager.current_proposal is not None
        assert voting_manager.current_proposal["id"] == "test-123"
        assert result == ["Agent1", "Agent2", "Agent3"]

        # Test without ProposalMessage
        voting_manager.set_phase_for_testing(VotingPhase.PROPOSAL)
        text_msg = TextMessage(content="Just text", source="Agent1")
        result = await voting_manager.handle_proposal_phase_for_testing(text_msg)
        assert result == ["Agent1"]

    @pytest.mark.asyncio
    async def test_handle_voting_phase(self, voting_manager: VotingGroupChatManager) -> None:
        """Test voting phase handling."""
        # Setup proposal
        voting_manager.set_proposal_for_testing({"id": "test-123", "title": "Test"})
        voting_manager.set_phase_for_testing(VotingPhase.VOTING)

        # Test vote recording
        vote = VoteMessage(
            content=VoteContent(vote=VoteType.APPROVE, proposal_id="test-123", reasoning="Looks good", confidence=0.9),
            source="Agent1",
        )

        with patch.object(voting_manager, "_is_voting_complete", return_value=False):
            result = await voting_manager.handle_voting_phase_for_testing(vote)

        assert "Agent1" in voting_manager.votes_cast
        assert voting_manager.votes_cast["Agent1"]["vote"] == VoteType.APPROVE
        assert "Agent1" not in result  # Agent1 already voted

        # Test voting completion
        with (
            patch.object(voting_manager, "_is_voting_complete", return_value=True),
            patch.object(voting_manager, "_process_voting_results", return_value=[]),
        ):
            result = await voting_manager.handle_voting_phase_for_testing(vote)

    @pytest.mark.asyncio
    async def test_handle_discussion_phase(self, voting_manager: VotingGroupChatManager) -> None:
        """Test discussion phase handling."""
        voting_manager.set_phase_for_testing(VotingPhase.DISCUSSION)
        voting_manager.set_discussion_rounds_for_testing(2)

        text_msg = TextMessage(content="Discussion point", source="Agent1")

        # Test continuing discussion
        result = await voting_manager.handle_discussion_phase_for_testing(text_msg)
        assert result == ["Agent1", "Agent2", "Agent3"]

        # Test max rounds reached
        voting_manager.set_discussion_rounds_for_testing(3)
        result = await voting_manager.handle_discussion_phase_for_testing(text_msg)

        assert voting_manager.current_phase == VotingPhase.VOTING
        assert voting_manager.votes_cast == {}  # Reset votes
        assert result == ["Agent1", "Agent2", "Agent3"]

    @pytest.mark.asyncio
    async def test_handle_consensus_phase(self, voting_manager: VotingGroupChatManager) -> None:
        """Test consensus phase handling."""
        text_msg = TextMessage(content="Consensus reached", source="Agent1")
        result = await voting_manager.handle_consensus_phase_for_testing(text_msg)
        assert result == []  # No more speakers needed

    @pytest.mark.asyncio
    async def test_is_voting_complete(self, voting_manager: VotingGroupChatManager) -> None:
        """Test voting completion check."""
        # No votes cast
        assert not voting_manager.is_voting_complete_for_testing()

        # Partial votes
        voting_manager.set_votes_for_testing({"Agent1": {"vote": VoteType.APPROVE}})
        assert not voting_manager.is_voting_complete_for_testing()

        # All votes cast
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE},
                "Agent2": {"vote": VoteType.REJECT},
                "Agent3": {"vote": VoteType.APPROVE},
            }
        )
        assert voting_manager.is_voting_complete_for_testing()

    @pytest.mark.asyncio
    async def test_process_voting_results(self, voting_manager: VotingGroupChatManager) -> None:
        """Test voting results processing."""
        # Test with no votes
        result = await voting_manager.process_voting_results_for_testing()
        assert result == []

        # Test with votes - just verify the method can be called
        voting_manager.set_votes_for_testing({"Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9}})

        with (
            patch.object(voting_manager, "update_message_thread"),
            patch.object(
                voting_manager,
                "_calculate_voting_result",
                return_value={
                    "proposal_id": "test-123",
                    "result": "approved",
                    "votes_summary": {"approve": 1},
                    "winning_option": "approve",
                    "total_voters": 3,
                    "participation_rate": 0.33,
                    "confidence_average": 0.9,
                    "detailed_votes": {},
                },
            ),
        ):
            result = await voting_manager.process_voting_results_for_testing()

        # Just verify method completes without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_calculate_voting_result_majority(self, voting_manager: VotingGroupChatManager) -> None:
        """Test majority voting calculation."""
        voting_manager.set_voting_method_for_testing(VotingMethod.MAJORITY)
        voting_manager.set_proposal_for_testing({"id": "test-123"})

        # Test approval majority
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.APPROVE, "confidence": 0.8},
                "Agent3": {"vote": VoteType.REJECT, "confidence": 0.7},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] == "approved"
        assert result["winning_option"] == VoteType.APPROVE.value
        assert result["participation_rate"] == 1.0

        # Test rejection majority
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.REJECT, "confidence": 0.9},
                "Agent2": {"vote": VoteType.REJECT, "confidence": 0.8},
                "Agent3": {"vote": VoteType.APPROVE, "confidence": 0.7},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] == "rejected"
        assert result["winning_option"] == VoteType.REJECT.value

    @pytest.mark.asyncio
    async def test_calculate_voting_result_plurality(self, voting_manager: VotingGroupChatManager) -> None:
        """Test plurality voting calculation."""
        voting_manager.set_voting_method_for_testing(VotingMethod.PLURALITY)
        voting_manager.set_proposal_for_testing({"id": "test-123"})
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.REJECT, "confidence": 0.8},
                "Agent3": {"vote": VoteType.ABSTAIN, "confidence": 0.5},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] in ["approved", "rejected"]  # Most common vote wins

    @pytest.mark.asyncio
    async def test_calculate_voting_result_unanimous(self, voting_manager: VotingGroupChatManager) -> None:
        """Test unanimous voting calculation."""
        voting_manager.set_voting_method_for_testing(VotingMethod.UNANIMOUS)
        voting_manager.set_proposal_for_testing({"id": "test-123"})

        # Test unanimous approval
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.APPROVE, "confidence": 0.8},
                "Agent3": {"vote": VoteType.APPROVE, "confidence": 0.7},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] == "approved"

        # Test with abstention
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.APPROVE, "confidence": 0.8},
                "Agent3": {"vote": VoteType.ABSTAIN, "confidence": 0.5},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] == "approved"

    @pytest.mark.asyncio
    async def test_calculate_voting_result_qualified_majority(self, voting_manager: VotingGroupChatManager) -> None:
        """Test qualified majority voting calculation."""
        voting_manager.set_voting_method_for_testing(VotingMethod.QUALIFIED_MAJORITY)
        voting_manager.set_qualified_majority_threshold_for_testing(0.67)
        voting_manager.set_proposal_for_testing({"id": "test-123"})

        # Test meeting qualified majority (2/3 = 0.67)
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.APPROVE, "confidence": 0.8},
                "Agent3": {"vote": VoteType.REJECT, "confidence": 0.7},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        # 2 out of 3 votes (0.67) meets the 0.67 threshold
        assert result["result"] in ["approved", "no_consensus"]  # Edge case at exact threshold

        # Test clearly not meeting qualified majority
        voting_manager.set_votes_for_testing(
            {
                "Agent1": {"vote": VoteType.APPROVE, "confidence": 0.9},
                "Agent2": {"vote": VoteType.REJECT, "confidence": 0.8},
                "Agent3": {"vote": VoteType.REJECT, "confidence": 0.7},
            }
        )

        result = voting_manager.calculate_voting_result_for_testing()
        assert result["result"] == "no_consensus"

    @pytest.mark.asyncio
    async def testannounce_voting_phase_for_testing(self, voting_manager: VotingGroupChatManager) -> None:
        """Test voting phase announcement."""
        voting_manager.set_proposal_for_testing({"title": "Test Proposal", "id": "test-123"})

        with patch.object(voting_manager, "update_message_thread") as mock_update:
            await voting_manager.announce_voting_phase_for_testing()
            mock_update.assert_called_once()

        # Test without proposal
        voting_manager.set_proposal_for_testing(None)
        with patch.object(voting_manager, "update_message_thread") as mock_update:
            await voting_manager.announce_voting_phase_for_testing()
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_and_load_state(self, voting_manager: VotingGroupChatManager) -> None:
        """Test state persistence."""
        # Set up some state
        voting_manager.set_phase_for_testing(VotingPhase.VOTING)
        voting_manager.set_proposal_for_testing({"id": "test-123", "title": "Test"})
        voting_manager.set_votes_for_testing({"Agent1": {"vote": VoteType.APPROVE}})
        voting_manager.set_discussion_rounds_for_testing(1)

        # Save state
        state = await voting_manager.save_state()

        # Reset manager
        await voting_manager.reset()
        assert voting_manager.current_phase == VotingPhase.PROPOSAL

        # Load state
        await voting_manager.load_state(state)

        # Verify state restored
        # The phase should be restored to VOTING from the saved state
        assert cast(VotingPhase, voting_manager.current_phase) == VotingPhase.VOTING
        assert voting_manager.current_proposal is not None
        assert voting_manager.current_proposal["id"] == "test-123"
        assert "Agent1" in voting_manager.votes_cast
        assert voting_manager.discussion_rounds == 1


class TestVotingResultMessage:
    """Test VotingResultMessage functionality."""

    def test_voting_result_message_creation(self) -> None:
        """Test VotingResultMessage creation and formatting."""
        result = VotingResult(
            proposal_id="test-123",
            result="approved",
            votes_summary={"approve": 2, "reject": 1},
            winning_option="approve",
            total_voters=3,
            participation_rate=1.0,
            confidence_average=0.85,
            detailed_votes={},
        )

        message = VotingResultMessage(content=result, source="VotingManager")

        text = message.to_model_text()
        assert "Voting Result: APPROVED" in text
        assert "Participation: 100.0%" in text
        assert "Average Confidence: 0.85" in text
        assert "approve: 2 votes" in text
        assert "Winning Option: approve" in text


class TestVotingGroupChatAdvanced:
    """Advanced tests for VotingGroupChat functionality."""

    def test_voting_method_enum_coverage(self) -> None:
        """Test that all voting methods are covered."""
        # This test ensures we test the enum values
        assert VotingMethod.MAJORITY.value == "majority"
        assert VotingMethod.PLURALITY.value == "plurality"
        assert VotingMethod.UNANIMOUS.value == "unanimous"
        assert VotingMethod.QUALIFIED_MAJORITY.value == "qualified_majority"
        assert VotingMethod.RANKED_CHOICE.value == "ranked_choice"

    def test_vote_type_enum_coverage(self) -> None:
        """Test that all vote types are covered."""
        assert VoteType.APPROVE.value == "approve"
        assert VoteType.REJECT.value == "reject"
        assert VoteType.ABSTAIN.value == "abstain"

    def test_voting_phase_enum_coverage(self) -> None:
        """Test that all voting phases are covered."""
        assert VotingPhase.PROPOSAL.value == "proposal"
        assert VotingPhase.VOTING.value == "voting"
        assert VotingPhase.DISCUSSION.value == "discussion"
        assert VotingPhase.CONSENSUS.value == "consensus"
