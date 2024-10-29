from typing import Sequence

from ..base import TerminatedException, TerminationCondition
from ..messages import ChatMessage, MultiModalMessage, StopMessage, TextMessage


class StopMessageTermination(TerminationCondition):
    """Terminate the conversation if a StopMessage is received."""

    def __init__(self) -> None:
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[ChatMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if isinstance(message, StopMessage):
                self._terminated = True
                return StopMessage(content="Stop message received", source="StopMessageTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False


class MaxMessageTermination(TerminationCondition):
    """Terminate the conversation after a maximum number of messages have been exchanged.

    Args:
        max_messages: The maximum number of messages allowed in the conversation.
    """

    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages
        self._message_count = 0

    @property
    def terminated(self) -> bool:
        return self._message_count >= self._max_messages

    async def __call__(self, messages: Sequence[ChatMessage]) -> StopMessage | None:
        if self.terminated:
            raise TerminatedException("Termination condition has already been reached")
        self._message_count += len(messages)
        if self._message_count >= self._max_messages:
            return StopMessage(
                content=f"Maximum number of messages {self._max_messages} reached, current message count: {self._message_count}",
                source="MaxMessageTermination",
            )
        return None

    async def reset(self) -> None:
        self._message_count = 0


class TextMentionTermination(TerminationCondition):
    """Terminate the conversation if a specific text is mentioned.

    Args:
        text: The text to look for in the messages.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[ChatMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if isinstance(message, TextMessage | StopMessage) and self._text in message.content:
                self._terminated = True
                return StopMessage(content=f"Text '{self._text}' mentioned", source="TextMentionTermination")
            elif isinstance(message, MultiModalMessage):
                for item in message.content:
                    if isinstance(item, str) and self._text in item:
                        self._terminated = True
                        return StopMessage(content=f"Text '{self._text}' mentioned", source="TextMentionTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False
