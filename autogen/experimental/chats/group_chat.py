from typing import AsyncGenerator, List, Optional, Union

from ..agent import Agent, AgentStream
from ..chat import ChatOrchestratorStream
from ..chat_summarizers.last_message import LastMessageSummarizer
from ..speaker_selection import SpeakerSelectionStrategy
from ..summarizer import ChatSummarizer
from ..termination import TerminationManager, TerminationResult
from ..termination_managers.default_termination_manager import DefaultTerminationManager
from ..types import (
    ChatResult,
    IntermediateResponse,
    Message,
    MessageAndSender,
    MessageContext,
    UserMessage,
    GenerateReplyResult,
)

DEFAULT_INTRO_MSG = (
    "Hello everyone. We have assembled a great team today to answer questions and solve tasks. In attendance are:"
)


def _introduction_message(agents: List[Agent], intro_message: str) -> str:
    participant_roles = [f"{agent.name}: {agent.description}".strip() for agent in agents]
    slash_n = "\n"
    return f"{intro_message}{slash_n}{slash_n}{slash_n.join(participant_roles)}"


class GroupChat(ChatOrchestratorStream):
    """(Experimental) This is a work in progress new interface for two person chats."""

    _termination_manager: TerminationManager
    _summarizer: ChatSummarizer

    def __init__(
        self,
        agents: List[Union[Agent, AgentStream]],
        *,
        speaker_selection: SpeakerSelectionStrategy,
        termination_manager: TerminationManager = DefaultTerminationManager(),
        summarizer: ChatSummarizer = LastMessageSummarizer(),
        initial_message: Optional[Union[str, Message, MessageAndSender]] = None,
        send_introduction: bool = True,
        intro_message: str = DEFAULT_INTRO_MSG,
    ):
        self._agents = agents
        self._speaker_selection = speaker_selection
        self._termination_manager = termination_manager
        self._termination_result: Optional[TerminationResult] = None
        self._summarizer = summarizer
        self._summary: Optional[str] = None

        self._finalize_done = False
        if isinstance(initial_message, str):
            initial_message = MessageAndSender(UserMessage(content=initial_message))
        self._chat_history: List[MessageAndSender] = []
        if send_introduction:
            self._chat_history.append(
                MessageAndSender(UserMessage(content=_introduction_message(agents, intro_message)))
            )

        if initial_message is not None:
            if isinstance(initial_message, str):
                initial_message = MessageAndSender(UserMessage(content=initial_message))
            if isinstance(initial_message, Message):
                initial_message = MessageAndSender(initial_message)
            self._chat_history.append(initial_message)

        self._chat_contexts: List[Optional[MessageContext]] = [] + [None] * len(self._chat_history)

        self._initial_chat_history = self._chat_history.copy()
        self._initial_chat_contexts = self._chat_contexts.copy()

        self._speaker: Agent = speaker_selection.select_speaker(self._agents, self._chat_history)

    async def _finalize(self, termination_result: TerminationResult) -> None:
        self._termination_result = termination_result
        self._summary = await self._summarizer.summarize_chat(self._chat_history, termination_result)
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
            chat_history=self._chat_history,
            # TODO incorporate message contexts
            message_contexts=[],
            summary=self._summary,
            termination_result=self._termination_result,
        )

    @property
    def termination_result(self) -> Optional[TerminationResult]:
        return self._termination_result

    @property
    def next_speaker(self) -> Agent:
        return self._speaker

    async def _handle_reply(self, reply: GenerateReplyResult) -> MessageAndSender:
        if isinstance(reply, tuple):
            message, context = reply
        else:
            message = reply
            context = None
        message_and_sender = MessageAndSender(message, sender=self._speaker)
        self._chat_history.append(message_and_sender)
        self._chat_contexts.append(context)
        self._termination_manager.record_turn_taken(self._speaker)
        self._speaker = self._speaker_selection.select_speaker(self._agents, self._chat_history)

        maybe_termination = await self._termination_manager.check_termination(self._chat_history)
        if maybe_termination is not None:
            await self._finalize(maybe_termination)

        return message_and_sender

    async def step(self) -> MessageAndSender:
        reply = await self._speaker.generate_reply(messages=self._chat_history)
        return await self._handle_reply(reply)

    async def stream_step(self) -> AsyncGenerator[Union[IntermediateResponse, MessageAndSender], None]:
        final_response = None
        if isinstance(self._speaker, AgentStream):
            async for response in self._speaker.stream_generate_reply(messages=self._chat_history):
                if not isinstance(response, IntermediateResponse):
                    final_response = await self._handle_reply(response)
                    break
                else:
                    yield response
        else:
            response = await self._speaker.generate_reply(messages=self._chat_history)
            final_response = await self._handle_reply(response)

        if final_response is None:
            raise ValueError("Final streamed response was not the final message.")

        yield final_response

    def append_message(self, message: MessageAndSender) -> None:
        self._chat_history.append(message)
        self._chat_contexts.append(None)

    @property
    def chat_history(self) -> List[MessageAndSender]:
        return self._chat_history

    @property
    def message_contexts(self) -> List[Optional[MessageContext]]:
        return self._chat_contexts

    def reset(self) -> None:
        self._chat_history = self._initial_chat_history.copy()
        self._chat_contexts = self._initial_chat_contexts.copy()
        self._termination_result = None
        self._finalize_done = False
        self._speaker = self._speaker_selection.select_speaker(self._agents, self._chat_history)
        self._termination_manager.reset()
        self._summary = None
