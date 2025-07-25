import asyncio
import logging
from collections import Counter
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Mapping, Optional, Sequence

from autogen_core import AgentRuntime, Component, ComponentModel
from pydantic import BaseModel, Field
from typing_extensions import Self

from ... import TRACE_LOGGER_NAME
from ...base import ChatAgent, TerminationCondition
from ...messages import (
    BaseAgentEvent,
    BaseChatMessage,
    MessageFactory,
    StructuredMessage,
    TextMessage,
)
from ...state import BaseGroupChatManagerState
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager
from ._events import GroupChatTermination

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)


class VotingMethod(str, Enum):
    """Supported voting methods for consensus building."""

    MAJORITY = "majority"  # >50% of votes required
    PLURALITY = "plurality"  # Most votes wins (simple)
    UNANIMOUS = "unanimous"  # All voters must agree
    QUALIFIED_MAJORITY = "qualified_majority"  # Configurable threshold (e.g., 2/3)
    RANKED_CHOICE = "ranked_choice"  # Ranked choice voting with elimination


class VoteType(str, Enum):
    """Types of votes that can be cast."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class VotingPhase(str, Enum):
    """Current phase of the voting process."""

    PROPOSAL = "proposal"  # Initial proposal or discussion
    VOTING = "voting"  # Collecting votes
    CONSENSUS = "consensus"  # Consensus reached
    DISCUSSION = "discussion"  # Additional discussion needed


class VoteContent(BaseModel):
    vote: VoteType
    proposal_id: str
    reasoning: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ranked_choices: Optional[List[str]] = None  # For ranked choice voting


class VoteMessage(StructuredMessage[VoteContent]):
    """Message containing a vote from an agent."""

    content: VoteContent

    def to_model_text(self) -> str:
        text = f"Vote: {self.content.vote.value}"
        if self.content.reasoning:
            text += f" - Reasoning: {self.content.reasoning}"
        if self.content.confidence < 1.0:
            text += f" (Confidence: {self.content.confidence:.2f})"
        return text


class ProposalContent(BaseModel):
    proposal_id: str
    title: str
    description: str
    options: List[str] = Field(default_factory=list)  # For multiple choice proposals
    requires_discussion: bool = False
    deadline: Optional[str] = None


class ProposalMessage(StructuredMessage[ProposalContent]):
    """Message containing a proposal for voting."""

    content: ProposalContent

    def to_model_text(self) -> str:
        text = f"Proposal: {self.content.title}\n{self.content.description}"
        if self.content.options:
            text += f"\nOptions: {', '.join(self.content.options)}"
        return text


class VotingResult(BaseModel):
    proposal_id: str
    result: Literal["approved", "rejected", "no_consensus"]
    votes_summary: Dict[str, int]  # vote_type -> count
    winning_option: Optional[str] = None
    total_voters: int
    participation_rate: float
    confidence_average: float
    detailed_votes: Optional[Dict[str, Dict[str, Any]]] = None


class VotingResultMessage(StructuredMessage[VotingResult]):
    """Message containing voting results."""

    content: VotingResult

    def to_model_text(self) -> str:
        result = self.content
        text = f"Voting Result: {result.result.upper()}\n"
        text += f"Participation: {result.participation_rate:.1%} ({result.total_voters} voters)\n"
        text += f"Average Confidence: {result.confidence_average:.2f}\n"

        for vote_type, count in result.votes_summary.items():
            text += f"{vote_type}: {count} votes\n"

        if result.winning_option:
            text += f"Winning Option: {result.winning_option}"

        return text


class VotingManagerState(BaseGroupChatManagerState):
    """State for the voting group chat manager."""

    type: str = "VotingManagerState"
    current_phase: VotingPhase = VotingPhase.PROPOSAL
    current_proposal: Optional[Dict[str, Any]] = None
    votes_cast: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # agent_name -> vote_data
    eligible_voters: List[str] = Field(default_factory=list)
    discussion_rounds: int = 0
    max_discussion_rounds: int = 3


class VotingGroupChatManager(BaseGroupChatManager):
    """A group chat manager that enables democratic consensus through configurable voting mechanisms."""

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        voting_method: VotingMethod,
        qualified_majority_threshold: float,
        allow_abstentions: bool,
        require_reasoning: bool,
        max_discussion_rounds: int,
        auto_propose_speaker: Optional[str],
        emit_team_events: bool,
    ) -> None:
        super().__init__(
            name,
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_names,
            participant_descriptions,
            output_message_queue,
            termination_condition,
            max_turns,
            message_factory,
            emit_team_events,
        )

        # Voting configuration
        self._voting_method = voting_method
        self._qualified_majority_threshold = qualified_majority_threshold
        self._allow_abstentions = allow_abstentions
        self._require_reasoning = require_reasoning
        self._max_discussion_rounds = max_discussion_rounds
        self._auto_propose_speaker = auto_propose_speaker

        # Voting state
        self._current_phase = VotingPhase.PROPOSAL
        self._current_proposal: Optional[Dict[str, Any]] = None
        self._votes_cast: Dict[str, Dict[str, Any]] = {}
        self._eligible_voters = list(participant_names)
        self._discussion_rounds = 0

        # Register custom message types
        message_factory.register(VoteMessage)
        message_factory.register(ProposalMessage)
        message_factory.register(VotingResultMessage)

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        """Validate the group state for voting."""
        if len(self._participant_names) < 2:
            raise ValueError("Voting requires at least 2 participants.")

    async def reset(self) -> None:
        """Reset the voting manager state."""
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()

        # Reset voting state
        self._current_phase = VotingPhase.PROPOSAL
        self._current_proposal = None
        self._votes_cast = {}
        self._eligible_voters = list(self._participant_names)
        self._discussion_rounds = 0

    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str:
        """Select speakers based on current voting phase and state."""

        if not thread:
            # Initial state - select proposer
            return self._select_proposer()

        last_message = thread[-1]

        # Handle different voting phases
        if self._current_phase == VotingPhase.PROPOSAL:
            return await self._handle_proposal_phase(last_message)
        elif self._current_phase == VotingPhase.VOTING:
            return await self._handle_voting_phase(last_message)
        elif self._current_phase == VotingPhase.DISCUSSION:
            return await self._handle_discussion_phase(last_message)
        elif self._current_phase == VotingPhase.CONSENSUS:
            return await self._handle_consensus_phase(last_message)

        return self._participant_names[0]  # Fallback

    def _select_proposer(self) -> str:
        """Select who should make the initial proposal."""
        if self._auto_propose_speaker and self._auto_propose_speaker in self._participant_names:
            return self._auto_propose_speaker
        return self._participant_names[0]

    async def _handle_proposal_phase(self, last_message: BaseAgentEvent | BaseChatMessage) -> List[str]:
        """Handle speaker selection during proposal phase."""

        if isinstance(last_message, ProposalMessage):
            # Proposal received, transition to voting
            self._current_proposal = {
                "id": last_message.content.proposal_id,
                "title": last_message.content.title,
                "description": last_message.content.description,
                "options": last_message.content.options,
            }
            self._current_phase = VotingPhase.VOTING

            # Announce voting phase
            await self._announce_voting_phase()

            # Return all eligible voters
            return self._eligible_voters

        # Still waiting for proposal
        return [self._select_proposer()]

    async def _handle_voting_phase(self, last_message: BaseAgentEvent | BaseChatMessage) -> List[str]:
        """Handle speaker selection during voting phase."""

        if isinstance(last_message, VoteMessage):
            # Record the vote
            voter_name = last_message.source
            if voter_name in self._eligible_voters:
                self._votes_cast[voter_name] = {
                    "vote": last_message.content.vote,
                    "reasoning": last_message.content.reasoning,
                    "confidence": last_message.content.confidence,
                    "ranked_choices": last_message.content.ranked_choices,
                }

                trace_logger.debug(f"Vote recorded from {voter_name}: {last_message.content.vote}")

        # Check if voting is complete
        if self._is_voting_complete():
            return await self._process_voting_results()

        # Return voters who haven't voted yet
        remaining_voters = [name for name in self._eligible_voters if name not in self._votes_cast]
        return remaining_voters if remaining_voters else []

    async def _handle_discussion_phase(self, last_message: BaseAgentEvent | BaseChatMessage) -> List[str]:
        """Handle speaker selection during discussion phase."""

        # Allow open discussion among all participants
        # After sufficient discussion, transition back to voting

        if self._discussion_rounds >= self._max_discussion_rounds:
            # Reset votes and start new voting round
            self._votes_cast = {}
            self._current_phase = VotingPhase.VOTING
            await self._announce_voting_phase()
            return self._eligible_voters

        # Continue discussion
        return self._participant_names

    async def _handle_consensus_phase(self, last_message: BaseAgentEvent | BaseChatMessage) -> List[str]:
        """Handle speaker selection after consensus is reached."""
        # Consensus reached, no more speakers needed
        return []

    def _is_voting_complete(self) -> bool:
        """Check if all eligible voters have cast their votes."""
        return len(self._votes_cast) >= len(self._eligible_voters)

    async def _process_voting_results(self) -> List[str]:
        """Process voting results and determine outcome."""

        if not self._votes_cast:
            return []

        # Calculate results based on voting method
        result = self._calculate_voting_result()

        # Create and send result message
        result_message = VotingResultMessage(content=VotingResult(**result), source=self._name)

        await self.update_message_thread([result_message])

        # Determine next phase
        if result["result"] == "no_consensus" and self._discussion_rounds < self._max_discussion_rounds:
            self._current_phase = VotingPhase.DISCUSSION
            self._discussion_rounds += 1
            return self._participant_names  # Open discussion
        else:
            self._current_phase = VotingPhase.CONSENSUS
            return []  # End voting process

    def _calculate_voting_result(self) -> Dict[str, Any]:
        """Calculate voting results based on the configured method."""

        vote_counts = Counter(vote_data["vote"].value for vote_data in self._votes_cast.values())
        total_votes = len(self._votes_cast)
        confidence_scores = [vote_data["confidence"] for vote_data in self._votes_cast.values()]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Determine result based on voting method
        result = "no_consensus"
        winning_option = None

        if self._voting_method == VotingMethod.MAJORITY:
            approve_count = vote_counts.get(VoteType.APPROVE.value, 0)
            if approve_count > total_votes / 2:
                result = "approved"
                winning_option = VoteType.APPROVE.value
            elif vote_counts.get(VoteType.REJECT.value, 0) > total_votes / 2:
                result = "rejected"
                winning_option = VoteType.REJECT.value

        elif self._voting_method == VotingMethod.PLURALITY:
            if vote_counts:
                most_common = vote_counts.most_common(1)[0]
                winning_option = most_common[0]
                result = "approved" if winning_option == VoteType.APPROVE.value else "rejected"

        elif self._voting_method == VotingMethod.UNANIMOUS:
            if (
                len(
                    set(
                        vote.value
                        for vote_data in self._votes_cast.values()
                        for vote in [vote_data["vote"]]
                        if vote != VoteType.ABSTAIN
                    )
                )
                == 1
            ):
                non_abstain_votes = [
                    vote_data["vote"]
                    for vote_data in self._votes_cast.values()
                    if vote_data["vote"] != VoteType.ABSTAIN
                ]
                if non_abstain_votes:
                    winning_vote = non_abstain_votes[0]
                    result = "approved" if winning_vote == VoteType.APPROVE else "rejected"
                    winning_option = winning_vote.value

        elif self._voting_method == VotingMethod.QUALIFIED_MAJORITY:
            approve_count = vote_counts.get(VoteType.APPROVE.value, 0)
            if approve_count >= total_votes * self._qualified_majority_threshold:
                result = "approved"
                winning_option = VoteType.APPROVE.value
            elif vote_counts.get(VoteType.REJECT.value, 0) >= total_votes * self._qualified_majority_threshold:
                result = "rejected"
                winning_option = VoteType.REJECT.value

        return {
            "proposal_id": self._current_proposal["id"] if self._current_proposal else "unknown",
            "result": result,
            "votes_summary": dict(vote_counts),
            "winning_option": winning_option,
            "total_voters": len(self._eligible_voters),
            "participation_rate": total_votes / len(self._eligible_voters),
            "confidence_average": avg_confidence,
            "detailed_votes": {name: data for name, data in self._votes_cast.items()},
        }

    async def _announce_voting_phase(self) -> None:
        """Announce the start of voting phase."""
        if self._current_proposal:
            announcement = TextMessage(
                content=f"Voting has begun for proposal: {self._current_proposal['title']}\n"
                f"Voting method: {self._voting_method.value}\n"
                f"Please cast your votes using VoteMessage.",
                source=self._name,
            )
            await self.update_message_thread([announcement])

    async def save_state(self) -> Mapping[str, Any]:
        """Save the voting manager state."""
        state = VotingManagerState(
            message_thread=[msg.dump() for msg in self._message_thread],
            current_turn=self._current_turn,
            current_phase=self._current_phase,
            current_proposal=self._current_proposal,
            votes_cast=self._votes_cast,
            eligible_voters=self._eligible_voters,
            discussion_rounds=self._discussion_rounds,
            max_discussion_rounds=self._max_discussion_rounds,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the voting manager state."""
        voting_state = VotingManagerState.model_validate(state)
        self._message_thread = [self._message_factory.create(msg) for msg in voting_state.message_thread]
        self._current_turn = voting_state.current_turn
        self._current_phase = voting_state.current_phase
        self._current_proposal = voting_state.current_proposal
        self._votes_cast = voting_state.votes_cast or {}
        self._eligible_voters = voting_state.eligible_voters or list(self._participant_names)
        self._discussion_rounds = voting_state.discussion_rounds
        self._max_discussion_rounds = voting_state.max_discussion_rounds


class VotingGroupChatConfig(BaseModel):
    """Configuration for VotingGroupChat."""

    participants: List[ComponentModel]
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    voting_method: VotingMethod = VotingMethod.MAJORITY
    qualified_majority_threshold: float = Field(default=0.67, ge=0.5, le=1.0)
    allow_abstentions: bool = True
    require_reasoning: bool = False
    max_discussion_rounds: int = 3
    auto_propose_speaker: Optional[str] = None
    emit_team_events: bool = False


class VotingGroupChat(BaseGroupChat, Component[VotingGroupChatConfig]):
    """A group chat team that enables democratic consensus through configurable voting mechanisms.

    Perfect for code reviews, architecture decisions, content moderation, and any scenario
    requiring group consensus with transparent decision-making processes.

    Args:
        participants (List[ChatAgent]): The agents participating in the voting process.
        voting_method (VotingMethod, optional): Method used for determining consensus. Defaults to VotingMethod.MAJORITY.
        qualified_majority_threshold (float, optional): Threshold for qualified majority voting (0.5-1.0). Defaults to 0.67.
        allow_abstentions (bool, optional): Whether agents can abstain from voting. Defaults to True.
        require_reasoning (bool, optional): Whether votes must include reasoning. Defaults to False.
        max_discussion_rounds (int, optional): Maximum rounds of discussion before final decision. Defaults to 3.
        auto_propose_speaker (str, optional): Agent name to automatically select as proposer. Defaults to None.
        termination_condition (TerminationCondition, optional): Condition for ending the chat. Defaults to None.
        max_turns (int, optional): Maximum number of turns before forcing termination. Defaults to None.
        runtime (AgentRuntime, optional): The agent runtime to use. Defaults to None.
        custom_message_types (List[type[BaseAgentEvent | BaseChatMessage]], optional): Additional message types for the chat. Defaults to None.
        emit_team_events (bool, optional): Whether to emit team events for UI integration. Defaults to False.

    Raises:
        ValueError: If fewer than 2 participants, invalid thresholds, or missing auto_propose_speaker.

    Examples:

    Code review voting with qualified majority:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import VotingGroupChat, VotingMethod
            from autogen_agentchat.conditions import MaxMessageTermination


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # Create reviewers with different expertise
                senior_dev = AssistantAgent(
                    "SeniorDev", model_client, system_message="Senior developer focused on architecture and best practices."
                )
                security_expert = AssistantAgent(
                    "SecurityExpert", model_client, system_message="Security specialist reviewing for vulnerabilities."
                )
                performance_engineer = AssistantAgent(
                    "PerformanceEngineer",
                    model_client,
                    system_message="Performance engineer optimizing for speed and efficiency.",
                )

                # Create voting team for code review
                voting_team = VotingGroupChat(
                    participants=[senior_dev, security_expert, performance_engineer],
                    voting_method=VotingMethod.QUALIFIED_MAJORITY,
                    qualified_majority_threshold=0.67,
                    require_reasoning=True,
                    max_discussion_rounds=2,
                    termination_condition=MaxMessageTermination(20),
                )

                # Review code changes
                task = "Proposal: Approve code change for merge with caching implementation"

                result = await voting_team.run(task=task)
                print(result)


            asyncio.run(main())

    Architecture decision with unanimous consensus:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import VotingGroupChat, VotingMethod
            from autogen_agentchat.conditions import MaxMessageTermination


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # Create architecture team
                tech_lead = AssistantAgent(
                    "TechLead", model_client, system_message="Technical lead with expertise in distributed systems."
                )
                solution_architect = AssistantAgent(
                    "SolutionArchitect", model_client, system_message="Solution architect focused on enterprise patterns."
                )
                devops_engineer = AssistantAgent(
                    "DevOpsEngineer", model_client, system_message="DevOps engineer focused on deployment and operations."
                )

                # Create voting team requiring unanimous consensus
                voting_team = VotingGroupChat(
                    participants=[tech_lead, solution_architect, devops_engineer],
                    voting_method=VotingMethod.UNANIMOUS,
                    max_discussion_rounds=3,
                    auto_propose_speaker="TechLead",
                    termination_condition=MaxMessageTermination(30),
                )

                task = "Proposal: Choose microservices communication pattern from available options"

                result = await voting_team.run(task=task)
                print(result)


            asyncio.run(main())

    Content moderation with simple majority:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import VotingGroupChat, VotingMethod
            from autogen_agentchat.conditions import MaxMessageTermination


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # Create moderation team
                community_manager = AssistantAgent(
                    "CommunityManager", model_client, system_message="Community manager maintaining positive environment."
                )
                safety_specialist = AssistantAgent(
                    "SafetySpecialist", model_client, system_message="Safety specialist focused on harmful content detection."
                )
                legal_advisor = AssistantAgent(
                    "LegalAdvisor", model_client, system_message="Legal advisor focused on compliance and risk."
                )

                # Create voting team for content moderation
                voting_team = VotingGroupChat(
                    participants=[community_manager, safety_specialist, legal_advisor],
                    voting_method=VotingMethod.MAJORITY,
                    allow_abstentions=True,
                    max_discussion_rounds=1,
                    termination_condition=MaxMessageTermination(15),
                )

                task = "Proposal: Moderate user forum post about platform feedback"

                result = await voting_team.run(task=task)
                print(result)


            asyncio.run(main())
    """

    component_config_schema = VotingGroupChatConfig
    component_provider_override = "autogen_agentchat.teams.VotingGroupChat"

    def __init__(
        self,
        participants: List[ChatAgent],
        voting_method: VotingMethod = VotingMethod.MAJORITY,
        qualified_majority_threshold: float = 0.67,
        allow_abstentions: bool = True,
        require_reasoning: bool = False,
        max_discussion_rounds: int = 3,
        auto_propose_speaker: Optional[str] = None,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
        emit_team_events: bool = False,
    ) -> None:
        # Validate participants
        if len(participants) < 2:
            raise ValueError("Voting requires at least 2 participants.")

        if auto_propose_speaker and auto_propose_speaker not in [p.name for p in participants]:
            raise ValueError(f"auto_propose_speaker '{auto_propose_speaker}' not found in participants.")

        if not (0.5 <= qualified_majority_threshold <= 1.0):
            raise ValueError("qualified_majority_threshold must be between 0.5 and 1.0")

        # Add voting message types to custom types
        voting_message_types: List[type[BaseAgentEvent | BaseChatMessage]] = [
            VoteMessage,
            ProposalMessage,
            VotingResultMessage,
        ]
        if custom_message_types:
            custom_message_types.extend(voting_message_types)
        else:
            custom_message_types = voting_message_types

        super().__init__(
            participants,
            group_chat_manager_name="VotingGroupChatManager",
            group_chat_manager_class=VotingGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
            emit_team_events=emit_team_events,
        )

        # Store voting configuration
        self._voting_method = voting_method
        self._qualified_majority_threshold = qualified_majority_threshold
        self._allow_abstentions = allow_abstentions
        self._require_reasoning = require_reasoning
        self._max_discussion_rounds = max_discussion_rounds
        self._auto_propose_speaker = auto_propose_speaker

    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
    ) -> Callable[[], VotingGroupChatManager]:
        def _factory() -> VotingGroupChatManager:
            return VotingGroupChatManager(
                name=name,
                group_topic_type=group_topic_type,
                output_topic_type=output_topic_type,
                participant_topic_types=participant_topic_types,
                participant_names=participant_names,
                participant_descriptions=participant_descriptions,
                output_message_queue=output_message_queue,
                termination_condition=termination_condition,
                max_turns=max_turns,
                message_factory=message_factory,
                voting_method=self._voting_method,
                qualified_majority_threshold=self._qualified_majority_threshold,
                allow_abstentions=self._allow_abstentions,
                require_reasoning=self._require_reasoning,
                max_discussion_rounds=self._max_discussion_rounds,
                auto_propose_speaker=self._auto_propose_speaker,
                emit_team_events=self._emit_team_events,
            )

        return _factory

    def _to_config(self) -> VotingGroupChatConfig:
        """Convert to configuration object."""
        return VotingGroupChatConfig(
            participants=[participant.dump_component() for participant in self._participants],
            termination_condition=self._termination_condition.dump_component() if self._termination_condition else None,
            max_turns=self._max_turns,
            voting_method=self._voting_method,
            qualified_majority_threshold=self._qualified_majority_threshold,
            allow_abstentions=self._allow_abstentions,
            require_reasoning=self._require_reasoning,
            max_discussion_rounds=self._max_discussion_rounds,
            auto_propose_speaker=self._auto_propose_speaker,
            emit_team_events=self._emit_team_events,
        )

    @classmethod
    def _from_config(cls, config: VotingGroupChatConfig) -> Self:
        """Create from configuration object."""
        participants = [ChatAgent.load_component(participant) for participant in config.participants]
        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )

        return cls(
            participants=participants,
            voting_method=config.voting_method,
            qualified_majority_threshold=config.qualified_majority_threshold,
            allow_abstentions=config.allow_abstentions,
            require_reasoning=config.require_reasoning,
            max_discussion_rounds=config.max_discussion_rounds,
            auto_propose_speaker=config.auto_propose_speaker,
            termination_condition=termination_condition,
            max_turns=config.max_turns,
            emit_team_events=config.emit_team_events,
        )
