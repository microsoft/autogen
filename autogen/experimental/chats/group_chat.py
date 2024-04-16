from typing import AsyncGenerator, List, Optional, Union

from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.chat_histories.chat_history_list import ChatHistoryList

from ..agent import Agent, AgentStream, GenerateReplyResult
from ..chat import ChatOrchestratorStream
from ..chat_summarizers.last_message import LastMessageSummarizer
from ..speaker_selection import SpeakerSelection
from ..summarizer import ChatSummarizer
from ..termination import Termination, TerminationResult
from ..termination_managers.default_termination_manager import DefaultTerminationManager
from ..types import (
    ChatResult,
    IntermediateResponse,
    Message,
    MessageContext,
    UserMessage,
)

import copy

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
        termination_manager: Termination = DefaultTerminationManager(),
        summarizer: ChatSummarizer = LastMessageSummarizer(),
        send_introduction: bool = True,
        intro_message: str = DEFAULT_INTRO_MSG,
    ):
        self._agents = agents
        self._speaker_selection = speaker_selection
        self._termination_manager = termination_manager
        self._termination_result: Optional[TerminationResult] = None
        self._summarizer = summarizer
        self._summary: Optional[str] = None
        self._conversation = ChatHistoryList()

        self._finalize_done = False

        if send_introduction:
            self._conversation.append_message(
                message=UserMessage(content=_introduction_message(agents, intro_message)), context=None
            )

        self._initial_conversation = copy.copy(self._conversation)

        self._speaker: Agent = speaker_selection.select_speaker(self._agents, self._conversation)

    async def _finalize(self, termination_result: TerminationResult) -> None:
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
    def termination_result(self) -> Optional[TerminationResult]:
        return self._termination_result

    @property
    def next_speaker(self) -> Agent:
        return self._speaker

    async def _handle_reply(self, reply: GenerateReplyResult) -> Message:
        if isinstance(reply, tuple):
            message, context = reply
            # We overwrite the context sender to be the current speaker
            context.sender = self._speaker
        else:
            message = reply
            context = None

        self._conversation.append_message(message, context=context)
        self._termination_manager.record_turn_taken(self._speaker)
        self._speaker = self._speaker_selection.select_speaker(self._agents, self._conversation)

        maybe_termination = await self._termination_manager.check_termination(self._conversation)
        if maybe_termination is not None:
            await self._finalize(maybe_termination)

        return message

    async def step(self) -> Message:
        reply = await self._speaker.generate_reply(self._conversation)
        return await self._handle_reply(reply)

    async def stream_step(self) -> AsyncGenerator[Union[IntermediateResponse, Message], None]:
        final_response = None
        if isinstance(self._speaker, AgentStream):
            async for response in self._speaker.stream_generate_reply(self._conversation):
                if not isinstance(response, IntermediateResponse):
                    final_response = await self._handle_reply(response)
                    break
                else:
                    yield response
        else:
            response = await self._speaker.generate_reply(self._conversation)
            final_response = await self._handle_reply(response)

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
        self._speaker = self._speaker_selection.select_speaker(self._agents, self._conversation)
        self._termination_manager.reset()
        self._summary = None
