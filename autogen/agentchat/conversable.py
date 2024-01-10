from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from autogen.code_utils import content_str


class Conversable(ABC):
    """An abstract implementation for the Conversable API.
    TODO: Currently the ConversableConversable class duck-types this API but
    should be refactored to use this implementation."""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
    ):
        self._name = name
        self._description = description
        self._chat_blocker = ChatBlocker()
        self._chat_counter = ChatCounter(max_consecutive_auto_reply)
        self._chat_messages = ChatMessages()
        if is_termination_msg is None:
            self._is_termination_msg = lambda msg: content_str(msg.get("content")) == "TERMINATE"
        else:
            self._is_termination_msg = is_termination_msg

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def chat_counter(self) -> ChatCounter:
        return self._chat_counter

    @property
    def chat_blocker(self) -> ChatBlocker:
        return self._chat_blocker

    @property
    def chat_messages(self) -> ChatMessages:
        return self._chat_messages

    def check_termination(self, message: Dict) -> bool:
        return self._is_termination_msg(message)

    @property
    def reply_at_receive(self) -> Dict[bool]:
        # NOTE: this property is for compatibility with ConversableConversable.
        return self.chat_blocker._reply_at_receive

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Conversable] = None) -> None:
        # NOTE: this property is for compatibility with ConversableConversable.
        self.chat_counter.reset(sender)

    def clear_history(self) -> None:
        # NOTE: this property is for compatibility with ConversableConversable.
        self.chat_messages.clear_history()

    def last_message(self, agent: Optional[Conversable] = None) -> Dict:
        # NOTE: this property is for compatibility with ConversableConversable.
        return self.chat_messages.get_last_message(agent)

    @abstractmethod
    def initiate_chat(self, recipient: Conversable, message: Dict) -> None:
        pass

    @abstractmethod
    def receive(self, message: Dict, sender: Conversable, request_reply: Optional[bool] = None):
        pass

    @abstractmethod
    def send(self, message: Dict, recipient: Conversable, request_reply: Optional[bool] = None):
        pass


class ChatMessages:
    """A delegate class for implementing message storage and retrieval."""

    def __init__(self) -> None:
        self._messages = defaultdict(list)

    @property
    def messages(self) -> Dict[Conversable, List[Dict]]:
        """A dictionary of conversations from agent to list of messages."""
        return self._messages

    def get_last_message(self, agent: Optional[Conversable] = None) -> Dict:
        """The last message exchanged with the agent.

        Args:
            agent (Conversable): The agent in the conversation.
                If None and more than one agent's conversations are found, an error will be raised.
                If None and only one conversation is found, the last message of the only conversation will be returned.

        Returns:
            The last message exchanged with the agent.
        """
        if agent is None:
            n_conversations = len(self._messages)
            if n_conversations == 0:
                return None
            if n_conversations == 1:
                for conversation in self._messages.values():
                    return conversation[-1]
            raise ValueError("More than one conversation is found. Please specify the sender to get the last message.")
        if agent not in self._messages.keys():
            raise KeyError(
                f"The agent '{agent.name}' is not present in any conversation. No history available for this agent."
            )
        return self._messages[agent][-1]

    def append_message(self, agent: Conversable, message: Dict) -> None:
        """Append a message to the conversation with the agent."""
        self._messages[agent].append(message)

    def clear_history(self, agent: Optional[Conversable] = None):
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear.
                If None, clear the chat history with all agents.
        """
        if agent is None:
            self._messages.clear()
        else:
            self._messages[agent].clear()


class ChatCounter:
    """A delegate class for implementing counter logic."""

    MAX_CONSECUTIVE_AUTO_REPLY = 100

    def __init__(self, max_consecutive_auto_reply: Optional[int] = None):
        if max_consecutive_auto_reply is not None:
            assert max_consecutive_auto_reply > 0
            self._maximum = max_consecutive_auto_reply
        else:
            self._maximum = self.MAX_CONSECUTIVE_AUTO_REPLY
        self._counter = defaultdict(int)

    def reset(self, sender: Optional[Conversable] = None):
        if sender is None:
            self._counter.clear()
        else:
            self._counter[sender] = 0

    def try_increment(self, sender: Conversable) -> bool:
        if self._counter[sender] >= self._maximum:
            return False
        self._counter[sender] += 1
        return True


class ChatBlocker:
    """A delegate class for implementing blocking logic."""

    def __init__(self):
        self._reply_at_receive = defaultdict(bool)

    def blocked(self, sender: Conversable) -> bool:
        """Check if the sender is blocked."""
        return not self._reply_at_receive[sender]

    def block(self, sender: Optional[Conversable] = None):
        """Blocks the sender or all senders if not given."""
        if sender is None:
            self._reply_at_receive.clear()
        else:
            self._reply_at_receive[sender] = False

    def unblock(self, sender: Conversable):
        """Unblock the sender."""
        self._reply_at_receive[sender] = True
