from typing import Callable, Dict, Optional, Protocol, TypeVar, Union
import warnings

from autogen.agentchat.chat import ChatResult
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.agentchat.utils import consolidate_chat_info, gather_usage_summary
from autogen.cache.abstract_cache_base import AbstractCache

S = TypeVar("S")
T = TypeVar("T")

class Conversation(Protocol[S, T]):
    def step() -> S:
        ...

    @property
    def done(self) -> bool:
        ...

    @property
    def result(self) -> T:
        ...

class TwoPersonChat(Conversation[Union[str, dict], ChatResult]):
    """(Experimental) This is a work in progress new interface for two person chats."""

    def __init__(
        self,
        sender: ConversableAgent,
        recipient: ConversableAgent,
        *,
        clear_history: bool = True,
        silent: Optional[bool] = False,
        cache: Optional[AbstractCache] = None,
        max_turns: Optional[int] = None,
        summary_method: Optional[Union[str, Callable]] = ConversableAgent.DEFAULT_SUMMARY_METHOD,
        summary_args: Optional[dict] = {},
        message: Optional[Union[Dict, str, Callable]] = None,
        **kwargs,
    ):
        warnings.warn(
            "TwoPersonChat is very experimental and subject to a change. Do not use *yet* unless you jzust want to try things.",
            FutureWarning,
        )
        self._sender = sender
        self._recipient = recipient
        self._clear_history = clear_history
        self._silent = silent
        self._cache = cache
        self._max_turns = max_turns
        self._current_turn = 0
        self._summary_method = summary_method
        self._summary_args = summary_args
        self._message = message
        self._kwargs = kwargs
        self._current_sender = sender
        self._current_recipient = recipient
        self._setup_done = False
        self._finalize_done = False

        consolidate_chat_info(
            {
                "recipient": self._recipient,
                "summary_method": self._summary_method,
            },
            uniform_sender=self,
        )

    def _setup(self) -> None:
        for agent in [self._sender, self._recipient]:
            agent._raise_exception_on_async_reply_functions()
            agent.client_cache = self._cache

        for agent in [self._sender, self._recipient]:
            agent._raise_exception_on_async_reply_functions()
            agent.client_cache = self._cache

        self._sender._prepare_chat(self._recipient, self._clear_history, reply_at_receive=False)
        if isinstance(self._message, Callable):
            initial_message = self._message(self._sender, self._recipient, self._kwargs)
        else:
            initial_message = self._sender.generate_init_message(self._message, **self._kwargs)

        if initial_message is None:
            raise ValueError("Initial message is None")

        self._sender.send(initial_message, self._recipient, request_reply=False, silent=self._silent)
        self._current_sender = self._recipient
        self._current_recipient = self._sender

        self._setup_done = True

    def _finalize(self) -> None:
        summary = self._sender._summarize_chat(
            self._summary_method,
            self._summary_args,
            self._recipient,
            cache=self._cache,
        )

        self._chat_result = ChatResult(
            chat_history=self._sender.chat_messages[self._recipient],
            summary=summary,
            cost=gather_usage_summary([self._sender, self._recipient]),
            human_input=self._sender._human_input,
        )


    def step(self) -> Union[str, dict]:
        if not self._setup_done:
            self._setup()

        def do_step() -> Union[str, dict, None]:
            reply = self._current_sender.generate_reply(sender=self._current_recipient)
            if reply is not None:
                self._current_sender.send(reply, self._current_recipient, request_reply=False, silent=self._silent)
            self._current_sender, self._current_recipient = self._current_recipient, self._current_sender
            return reply

        if self._max_turns is not None:
            if self._current_turn < self._max_turns:
                reply = do_step()
                self._current_turn += 1
            else:
                raise ValueError("Max turns reached")
        else:
            reply = do_step()

        if reply is None:
            self._finalize()

        return reply

def run(conversation: Conversation[S, T]) -> T:
    while not conversation.done:
        conversation.step()
    return conversation.result
