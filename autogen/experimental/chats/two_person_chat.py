from typing import Callable, Dict, List, Optional, Protocol, TypeVar, Union
import warnings

from autogen.experimental.chat_summarizers.last_message import LastMessageSummarizer
from autogen.experimental.termination import TerminationManager, TerminationResult
from autogen.experimental.termination_managers.default_termination_manager import DefaultTerminationManager

from ..summarizer import ChatSummarizer
from ..chat import Chat
from ..agent import Agent
from ..types import ChatMessage, UserMessage

import asyncio


class TwoPersonChat(Chat):
    """(Experimental) This is a work in progress new interface for two person chats."""

    _termination_manager: TerminationManager
    _summarizer: ChatSummarizer

    def __init__(
        self,
        first: Agent,
        second: Agent,
        *,
        termination_manager: TerminationManager = DefaultTerminationManager(),
        summarizer: ChatSummarizer = LastMessageSummarizer(),
        initial_message: Optional[Union[str, ChatMessage]] = None
    ):
        self._agents = [first, second]
        self._current_agent_index = 0
        self._termination_manager = termination_manager
        self._termination_result: Optional[TerminationResult] = None

        self._summarizer = summarizer
        self._summary: Optional[str] = None
        self._finalize_done = False
        if isinstance(initial_message, str):
            initial_message = UserMessage(content=initial_message)
        self._chat_history = [initial_message] if initial_message is not None else []

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

    async def step(self) -> ChatMessage:
        next_to_reply = self._agents[self._current_agent_index]
        reply = await next_to_reply.generate_reply(messages=self._chat_history)
        self._chat_history.append(reply)
        self._termination_manager.record_turn_taken(next_to_reply)
        self._current_agent_index = (self._current_agent_index + 1) % len(self._agents)

        maybe_termination = await self._termination_manager.check_termination(self._chat_history)
        if maybe_termination is not None:
            await self._finalize(maybe_termination)

        return reply

    def step_sync(self) -> ChatMessage:
        return asyncio.run(self.step())

    def append_message(self, message: ChatMessage) -> None:
        self._chat_history.append(message)

    @property
    def chat_history(self) -> List[ChatMessage]:
        return self._chat_history
