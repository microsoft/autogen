from typing import Sequence

from ..base import TerminatedException, TerminationCondition
from ..messages import AgentMessage, MultiModalMessage, StopMessage, TextMessage


class StopMessageTermination(TerminationCondition):
    """Terminate the conversation if a StopMessage is received."""

    def __init__(self) -> None:
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
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

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
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

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
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


class TokenUsageTermination(TerminationCondition):
    """Terminate the conversation if a token usage limit is reached.

    Args:
        max_total_token: The maximum total number of tokens allowed in the conversation.
        max_prompt_token: The maximum number of prompt tokens allowed in the conversation.
        max_completion_token: The maximum number of completion tokens allowed in the conversation.

    Raises:
        ValueError: If none of max_total_token, max_prompt_token, or max_completion_token is provided.
    """

    def __init__(
        self,
        max_total_token: int | None = None,
        max_prompt_token: int | None = None,
        max_completion_token: int | None = None,
    ) -> None:
        if max_total_token is None and max_prompt_token is None and max_completion_token is None:
            raise ValueError(
                "At least one of max_total_token, max_prompt_token, or max_completion_token must be provided"
            )
        self._max_total_token = max_total_token
        self._max_prompt_token = max_prompt_token
        self._max_completion_token = max_completion_token
        self._total_token_count = 0
        self._prompt_token_count = 0
        self._completion_token_count = 0

    @property
    def terminated(self) -> bool:
        return (
            (self._max_total_token is not None and self._total_token_count >= self._max_total_token)
            or (self._max_prompt_token is not None and self._prompt_token_count >= self._max_prompt_token)
            or (self._max_completion_token is not None and self._completion_token_count >= self._max_completion_token)
        )

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self.terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if message.models_usage is not None:
                self._prompt_token_count += message.models_usage.prompt_tokens
                self._completion_token_count += message.models_usage.completion_tokens
                self._total_token_count += message.models_usage.prompt_tokens + message.models_usage.completion_tokens
        if self.terminated:
            content = f"Token usage limit reached, total token count: {self._total_token_count}, prompt token count: {self._prompt_token_count}, completion token count: {self._completion_token_count}."
            return StopMessage(content=content, source="TokenUsageTermination")
        return None

    async def reset(self) -> None:
        self._total_token_count = 0
        self._prompt_token_count = 0
        self._completion_token_count = 0
