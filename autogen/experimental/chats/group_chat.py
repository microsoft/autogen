from typing import AsyncGenerator, Callable, Dict, List, Optional, Protocol, TypeVar, Union
import warnings

from ..chat_summarizers.last_message import LastMessageSummarizer
from ..speaker_selection import SpeakerSelectionStrategy
from ..termination import TerminationManager, TerminationResult
from ..termination_managers.default_termination_manager import DefaultTerminationManager

from ..summarizer import ChatSummarizer
from ..chat import Chat, ChatStream
from ..agent import Agent, AgentStream
from ..types import AssistantMessage, ChatMessage, StreamResponse, SystemMessage, ToolMessage, UserMessage

DEFAULT_INTRO_MSG = (
    "Hello everyone. We have assembled a great team today to answer questions and solve tasks. In attendance are:"
)


def _introduction_message(agents: List[Agent], intro_message: str) -> str:
    participant_roles = [f"{agent.name}: {agent.description}".strip() for agent in agents]
    slash_n = "\n"
    return f"{intro_message}{slash_n}{slash_n}{slash_n.join(participant_roles)}"


class GroupChat(ChatStream):
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
        initial_message: Optional[Union[str, ChatMessage]] = None,
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
            initial_message = UserMessage(content=initial_message)
        self._chat_history: List[ChatMessage] = []
        if send_introduction:
            self._chat_history.append(UserMessage(content=_introduction_message(agents, intro_message)))

        if initial_message is not None:
            if isinstance(initial_message, str):
                initial_message = UserMessage(content=initial_message)
            self._chat_history.append(initial_message)

        self._speaker = speaker_selection.select_speaker(None, self._agents, self._chat_history)

    async def _finalize(self, termination_result: TerminationResult) -> None:
        self._termination_result = termination_result
        self._summary = await self._summarizer.summarize_chat(self._chat_history, termination_result)
        self._finalize_done = True

    @property
    def done(self) -> bool:
        return self._finalize_done

    @property
    def result(self) -> str:
        if not self.done:
            raise ValueError("Chat is not done yet.")

        assert self._summary is not None
        return self._summary

    @property
    def termination_result(self) -> Optional[TerminationResult]:
        return self._termination_result

    @property
    def next_speaker(self) -> Agent:
        return self._speaker

    async def step(self) -> ChatMessage:

        reply = await self._speaker.generate_reply(messages=self._chat_history)
        self._chat_history.append(reply)
        self._termination_manager.record_turn_taken(self._speaker)
        self._speaker = self._speaker_selection.select_speaker(self._speaker, self._agents, self._chat_history)

        maybe_termination = await self._termination_manager.check_termination(self._chat_history)
        if maybe_termination is not None:
            await self._finalize(maybe_termination)

        return reply

    async def stream_step(self) -> AsyncGenerator[StreamResponse, None]:

        async def handle_response(response: ChatMessage) -> None:
            self._chat_history.append(response)
            self._termination_manager.record_turn_taken(self._speaker)
            self._speaker = self._speaker_selection.select_speaker(self._speaker, self._agents, self._chat_history)

            maybe_termination = await self._termination_manager.check_termination(self._chat_history)
            if maybe_termination is not None:
                await self._finalize(maybe_termination)

        final_response = None
        if isinstance(self._speaker, AgentStream):
            async for response in self._speaker.stream_generate_reply(messages=self._chat_history):
                if isinstance(response, (SystemMessage, UserMessage, AssistantMessage, ToolMessage)):
                    await handle_response(response)
                    final_response = response
                    break
                else:
                    yield response
        else:
            response = await self._speaker.generate_reply(messages=self._chat_history)
            await handle_response(response)
            final_response = response

        if final_response is None:
            raise ValueError("Final streamed response was not the final message.")

        yield final_response

    def append_message(self, message: ChatMessage) -> None:
        self._chat_history.append(message)

    @property
    def chat_history(self) -> List[ChatMessage]:
        return self._chat_history
