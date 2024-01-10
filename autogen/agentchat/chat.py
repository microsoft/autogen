from __future__ import annotations
from typing import Dict, Optional
from autogen.agentchat import Agent
from autogen.agentchat.conversable import Conversable
from autogen.agentchat.conversable_agent import ConversableAgent


class Chat(Conversable):
    """A Conversable type that delegates to a chat between two Conversable objects
    (e.g., ConversableAgent or another Chat)."""

    def __init__(
        self,
        sender: Conversable,
        receiver: Conversable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_consecutive_auto_reply: Optional[int] = None,
    ):
        self._sender = sender
        self._receiver = receiver
        if name is None:
            name = f"{sender.name}+{receiver.name}"
        super().__init__(
            name=name,
            description=description,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
        )

    def initiate_chat(self, recipient: Conversable, message: Dict) -> None:
        self.chat_counter.reset(recipient)
        self.chat_blocker.unblock(recipient)
        if isinstance(recipient, ConversableAgent):
            # NOTE: Special handling for ConversableAgent.
            # Remove this once we refactor ConversableAgent to use Conversable.
            recipient.reset_consecutive_auto_reply_counter(self)
            recipient.reply_at_receive[self] = True
        else:
            recipient.chat_counter.reset(self)
            recipient.chat_blocker.unblock(self)

        # Use the input message as the first message.
        # TODO: add preparation mechanism.
        self.send(message, recipient)

    def clear_history(self) -> None:
        self.chat_messages.clear_history()
        self._sender.clear_history()
        self._receiver.clear_history()

    def receive(self, message: Dict, sender: Agent, request_reply: Optional[bool] = None):
        self.chat_messages.append_message(sender, message)
        if self.check_termination(message) or not self.chat_counter.try_increment(sender):
            return
        # TODO: add preparation mechanism to prepare the inner chat.
        # Run inner chat using the input message from outer sender.
        self._sender.initiate_chat(self._receiver, message=message)
        # Skip reply if not requested.
        if request_reply is False or request_reply is None and self.chat_blocker.blocked(sender):
            return
        # Take the last message received by the inner sender as the final reply message.
        # TODO: add reflection mechanism and handle no message received by the inner sender.
        reply = self._sender.last_message(self._receiver)
        # Send the reply to the outer sender.
        self.send(reply, sender)

    def send(self, message: Dict, recipient: Agent, request_reply: Optional[bool] = None):
        self.chat_messages.append_message(recipient, message)
        recipient.receive(message, self, request_reply)
