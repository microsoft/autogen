import asyncio
import copy
from typing import AsyncGenerator, List, Optional, Tuple, Union, cast

from ..agent import Agent, AgentStream
from ..chat import ChatOrchestratorStream
from ..chat_histories.chat_history_list import ChatHistoryList
from ..chat_history import ChatHistoryReadOnly
from ..chat_result import ChatResult
from ..chat_summarizers.last_message import LastMessageSummarizer
from ..speaker_selection import SpeakerSelection
from ..summarizer import ChatSummarizer
from ..termination import Terminated, Termination
from ..terminations.default_termination import DefaultTermination
from ..types import GenerateReplyResult, IntermediateResponse, Message, MessageContext, UserMessage

DEFAULT_INTRO_MSG = (
    "Hello everyone. We have assembled a great team today to answer questions and solve tasks. In attendance are:"
)


def _introduction_message(agents: List[Agent], intro_message: str) -> str:
    participant_roles = [f"{agent.name}: {agent.description}".strip() for agent in agents]
    slash_n = "\n"
    return f"{intro_message}{slash_n}{slash_n}{slash_n.join(participant_roles)}"


class GroupChat(ChatOrchestratorStream):
    """(Experimental) This is a work in progress new interface for two person chats."""

    _termination_manager: Termination
    _summarizer: ChatSummarizer

    def __init__(
        self,
        agents: List[Union[Agent, AgentStream]],
        *,
        speaker_selection: SpeakerSelection,
        termination_manager: Termination = DefaultTermination(),
        summarizer: ChatSummarizer = LastMessageSummarizer(),
        send_introduction: bool = True,
        intro_message: str = DEFAULT_INTRO_MSG,
    ):
        self._agents = agents
        self._speaker_selection = speaker_selection
        self._termination_manager = termination_manager
        self._termination_result: Optional[Terminated] = None
        self._summarizer = summarizer
        self._summary: Optional[str] = None
        self._conversation = ChatHistoryList()

        self._finalize_done = False

        self._speaker: Optional[Agent] = None

        if send_introduction:
            self._conversation.append_message(
                message=UserMessage(content=_introduction_message(agents, intro_message)), context=None
            )

        self._initial_conversation = copy.copy(self._conversation)

    async def _finalize(self, termination_result: Terminated) -> None:
        self._termination_result = termination_result
        self._summary = await self._summarizer.summarize_chat(self._conversation, termination_result)
        self._finalize_done = True

    @property
    def done(self) -> bool:
        return self._finalize_done

    @property
    def result(self) -> ChatResult:
        if not self.done:
            raise ValueError("ChatOrchestrator is not done yet.")

        assert self._summary is not None
        assert self._termination_result is not None
        return ChatResult(
            conversation=self._conversation,
            summary=self._summary,
            termination_result=self._termination_result,
        )

    @property
    def termination_result(self) -> Optional[Terminated]:
        return self._termination_result

    async def _handle_reply(self, reply: GenerateReplyResult, speaker_selection_reason: Optional[str]) -> Message:
        if isinstance(reply, tuple):
            message, context = reply
            # We overwrite the context sender to be the current speaker
            context.sender = self._speaker
        else:
            message = reply
            # TODO add input etc
            context = MessageContext(sender=self._speaker)

        assert self._speaker is not None, "Speaker should only ever be None at initialization."
        self._termination_manager.record_turn_taken(self._speaker)

        maybe_termination = await self._termination_manager.check_termination(self._conversation)
        context.termination_result = maybe_termination
        context.speaker_selection_reason = speaker_selection_reason
        self._conversation.append_message(message, context=context)
        if isinstance(maybe_termination, Terminated):
            await self._finalize(maybe_termination)

        return message

    async def _select_next_speaker(self) -> Tuple[Agent, Optional[str]]:
        next_agent: Union[Agent, Tuple[Agent, str]]
        if asyncio.iscoroutinefunction(self._speaker_selection.select_speaker):
            next_agent = await self._speaker_selection.select_speaker(self._agents, self._conversation)
            if isinstance(next_agent, tuple):
                next_agent, reason = next_agent
                return next_agent, reason
            else:
                return next_agent, None
        else:
            next_agent = cast(
                Union[Agent, Tuple[Agent, str]],
                self._speaker_selection.select_speaker(self._agents, self._conversation),
            )
            if isinstance(next_agent, tuple):
                next_agent, reason = next_agent
                return next_agent, reason
            else:
                return next_agent, None

    async def step(self) -> Message:
        self._speaker, reason = await self._select_next_speaker()
        reply = await self._speaker.generate_reply(self._conversation)
        return await self._handle_reply(reply, reason)

    async def stream_step(self) -> AsyncGenerator[Union[IntermediateResponse, Message], None]:
        self._speaker, reason = await self._select_next_speaker()
        final_response = None
        if isinstance(self._speaker, AgentStream):
            async for response in self._speaker.stream_generate_reply(self._conversation):
                if not isinstance(response, IntermediateResponse):
                    final_response = await self._handle_reply(response, reason)
                    break
                else:
                    yield response
        else:
            response = await self._speaker.generate_reply(self._conversation)
            final_response = await self._handle_reply(response, reason)

        if final_response is None:
            raise ValueError("Final streamed response was not the final message.")

        yield final_response

    def append_message(self, message: Message, context: Optional[MessageContext] = None) -> None:
        self._conversation.append_message(message, context=context)

    @property
    def chat_history(self) -> ChatHistoryReadOnly:
        return self._conversation

    def reset(self) -> None:
        self._conversation = copy.copy(self._initial_conversation)
        self._termination_result = None
        self._finalize_done = False
        self._speaker = None
        self._termination_manager.reset()
        self._summary = None
