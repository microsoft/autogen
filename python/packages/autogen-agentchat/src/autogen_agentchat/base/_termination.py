import asyncio
from abc import ABC, abstractmethod
from typing import List, Sequence

from ..messages import AgentMessage, StopMessage


class TerminatedException(BaseException): ...


class TerminationCondition(ABC):
    """A stateful condition that determines when a conversation should be terminated.

    A termination condition is a callable that takes a sequence of ChatMessage objects
    since the last time the condition was called, and returns a StopMessage if the
    conversation should be terminated, or None otherwise.
    Once a termination condition has been reached, it must be reset before it can be used again.

    Termination conditions can be combined using the AND and OR operators.

    Example:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.task import MaxMessageTermination, TextMentionTermination


            async def main() -> None:
                # Terminate the conversation after 10 turns or if the text "TERMINATE" is mentioned.
                cond1 = MaxMessageTermination(10) | TextMentionTermination("TERMINATE")

                # Terminate the conversation after 10 turns and if the text "TERMINATE" is mentioned.
                cond2 = MaxMessageTermination(10) & TextMentionTermination("TERMINATE")

                # ...

                # Reset the termination condition.
                await cond1.reset()
                await cond2.reset()


            asyncio.run(main())
    """

    @property
    @abstractmethod
    def terminated(self) -> bool:
        """Check if the termination condition has been reached"""
        ...

    @abstractmethod
    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        """Check if the conversation should be terminated based on the messages received
        since the last time the condition was called.
        Return a StopMessage if the conversation should be terminated, or None otherwise.

        Args:
            messages: The messages received since the last time the condition was called.

        Returns:
            StopMessage | None: A StopMessage if the conversation should be terminated, or None otherwise.

        Raises:
            TerminatedException: If the termination condition has already been reached."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the termination condition."""
        ...

    def __and__(self, other: "TerminationCondition") -> "TerminationCondition":
        """Combine two termination conditions with an AND operation."""
        return _AndTerminationCondition(self, other)

    def __or__(self, other: "TerminationCondition") -> "TerminationCondition":
        """Combine two termination conditions with an OR operation."""
        return _OrTerminationCondition(self, other)


class _AndTerminationCondition(TerminationCondition):
    def __init__(self, *conditions: TerminationCondition) -> None:
        self._conditions = conditions
        self._stop_messages: List[StopMessage] = []

    @property
    def terminated(self) -> bool:
        return all(condition.terminated for condition in self._conditions)

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self.terminated:
            raise TerminatedException("Termination condition has already been reached.")
        # Check all remaining conditions.
        stop_messages = await asyncio.gather(
            *[condition(messages) for condition in self._conditions if not condition.terminated]
        )
        # Collect stop messages.
        for stop_message in stop_messages:
            if stop_message is not None:
                self._stop_messages.append(stop_message)
        if any(stop_message is None for stop_message in stop_messages):
            # If any remaining condition has not reached termination, it is not terminated.
            return None
        content = ", ".join(stop_message.content for stop_message in self._stop_messages)
        source = ", ".join(stop_message.source for stop_message in self._stop_messages)
        return StopMessage(content=content, source=source)

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()
        self._stop_messages.clear()


class _OrTerminationCondition(TerminationCondition):
    def __init__(self, *conditions: TerminationCondition) -> None:
        self._conditions = conditions

    @property
    def terminated(self) -> bool:
        return any(condition.terminated for condition in self._conditions)

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self.terminated:
            raise RuntimeError("Termination condition has already been reached")
        stop_messages = await asyncio.gather(*[condition(messages) for condition in self._conditions])
        if any(stop_message is not None for stop_message in stop_messages):
            content = ", ".join(stop_message.content for stop_message in stop_messages if stop_message is not None)
            source = ", ".join(stop_message.source for stop_message in stop_messages if stop_message is not None)
            return StopMessage(content=content, source=source)
        return None

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()
