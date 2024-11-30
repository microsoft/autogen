import time
from typing import List, Sequence

from ..base import TerminatedException, TerminationCondition
from ..messages import AgentMessage, HandoffMessage, MultiModalMessage, StopMessage, TextMessage
from ..state._termination_states import (
    BaseTerminationState,
    ExternalTerminationState,
    HandoffTerminationState,
    MaxMessageTerminationState,
    SourceMatchTerminationState,
    StopMessageTerminationState,
    TextMentionTerminationState,
    TimeoutTerminationState,
    TokenUsageTerminationState,
)


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

    async def save_state(self) -> StopMessageTerminationState:
        return StopMessageTerminationState(terminated=self._terminated)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, StopMessageTerminationState):
            raise ValueError(f"Expected StopMessageTerminationState, got {type(state)}")
        self._terminated = state.terminated


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

    async def save_state(self) -> MaxMessageTerminationState:
        return MaxMessageTerminationState(message_count=self._message_count, max_messages=self._max_messages)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, MaxMessageTerminationState):
            raise ValueError(f"Expected MaxMessageTerminationState, got {type(state)}")
        self._message_count = state.message_count
        self._max_messages = state.max_messages


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

    async def save_state(self) -> TextMentionTerminationState:
        return TextMentionTerminationState(terminated=self._terminated, text=self._text)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, TextMentionTerminationState):
            raise ValueError(f"Expected TextMentionTerminationState, got {type(state)}")
        self._terminated = state.terminated
        self._text = state.text


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

    async def save_state(self) -> TokenUsageTerminationState:
        return TokenUsageTerminationState(
            total_token_count=self._total_token_count,
            prompt_token_count=self._prompt_token_count,
            completion_token_count=self._completion_token_count,
            max_total_token=self._max_total_token,
            max_prompt_token=self._max_prompt_token,
            max_completion_token=self._max_completion_token,
        )

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, TokenUsageTerminationState):
            raise ValueError(f"Expected TokenUsageTerminationState, got {type(state)}")
        self._total_token_count = state.total_token_count
        self._prompt_token_count = state.prompt_token_count
        self._completion_token_count = state.completion_token_count
        self._max_total_token = state.max_total_token
        self._max_prompt_token = state.max_prompt_token
        self._max_completion_token = state.max_completion_token


class HandoffTermination(TerminationCondition):
    """Terminate the conversation if a :class:`~autogen_agentchat.messages.HandoffMessage`
    with the given target is received.

    Args:
        target (str): The target of the handoff message.
    """

    def __init__(self, target: str) -> None:
        self._terminated = False
        self._target = target

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for message in messages:
            if isinstance(message, HandoffMessage) and message.target == self._target:
                self._terminated = True
                return StopMessage(
                    content=f"Handoff to {self._target} from {message.source} detected.", source="HandoffTermination"
                )
        return None

    async def reset(self) -> None:
        self._terminated = False

    async def save_state(self) -> HandoffTerminationState:
        return HandoffTerminationState(terminated=self._terminated, target=self._target)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, HandoffTerminationState):
            raise ValueError(f"Expected HandoffTerminationState, got {type(state)}")
        self._terminated = state.terminated
        self._target = state.target


class TimeoutTermination(TerminationCondition):
    """Terminate the conversation after a specified duration has passed.

    Args:
        timeout_seconds: The maximum duration in seconds before terminating the conversation.
    """

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds
        self._start_time = time.monotonic()
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")

        if (time.monotonic() - self._start_time) >= self._timeout_seconds:
            self._terminated = True
            return StopMessage(
                content=f"Timeout of {self._timeout_seconds} seconds reached", source="TimeoutTermination"
            )
        return None

    async def reset(self) -> None:
        self._start_time = time.monotonic()
        self._terminated = False

    async def save_state(self) -> TimeoutTerminationState:
        return TimeoutTerminationState(
            terminated=self._terminated, start_time=self._start_time, timeout_seconds=self._timeout_seconds
        )

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, TimeoutTerminationState):
            raise ValueError(f"Expected TimeoutTerminationState, got {type(state)}")
        self._terminated = state.terminated
        self._start_time = state.start_time
        self._timeout_seconds = state.timeout_seconds


class ExternalTermination(TerminationCondition):
    """A termination condition that is externally controlled
    by calling the :meth:`set` method.

    Example:

    .. code-block:: python

        from autogen_agentchat.task import ExternalTermination

        termination = ExternalTermination()

        # Run the team in an asyncio task.
        ...

        # Set the termination condition externally
        termination.set()

    """

    def __init__(self) -> None:
        self._terminated = False
        self._setted = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    def set(self) -> None:
        """Set the termination condition to terminated."""
        self._setted = True

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        if self._setted:
            self._terminated = True
            return StopMessage(content="External termination requested", source="ExternalTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False
        self._setted = False

    async def save_state(self) -> ExternalTerminationState:
        return ExternalTerminationState(terminated=self._terminated, setted=self._setted)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, ExternalTerminationState):
            raise ValueError(f"Expected ExternalTerminationState, got {type(state)}")
        self._terminated = state.terminated
        self._setted = state.setted


class SourceMatchTermination(TerminationCondition):
    """Terminate the conversation after a specific source responds.

    Args:
        sources (List[str]): List of source names to terminate the conversation.

    Raises:
        TerminatedException: If the termination condition has already been reached.
    """

    def __init__(self, sources: List[str]) -> None:
        self._sources = sources
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        if not messages:
            return None
        for message in messages:
            if message.source in self._sources:
                self._terminated = True
                return StopMessage(content=f"'{message.source}' answered", source="SourceMatchTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False

    async def save_state(self) -> SourceMatchTerminationState:
        return SourceMatchTerminationState(terminated=self._terminated, sources=self._sources)

    async def load_state(self, state: BaseTerminationState) -> None:
        if not isinstance(state, SourceMatchTerminationState):
            raise ValueError(f"Expected SourceMatchTerminationState, got {type(state)}")
        self._terminated = state.terminated
        self._sources = state.sources
