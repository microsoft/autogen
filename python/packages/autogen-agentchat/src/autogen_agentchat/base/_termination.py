import asyncio
from abc import ABC, abstractmethod
from typing import List, Sequence

from autogen_core import Component, ComponentBase, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from ..messages import BaseAgentEvent, BaseChatMessage, StopMessage


class TerminatedException(BaseException): ...


class TerminationCondition(ABC, ComponentBase[BaseModel]):
    """A stateful condition that determines when a conversation should be terminated.

    A termination condition is a callable that takes a sequence of ChatMessage objects
    since the last time the condition was called, and returns a StopMessage if the
    conversation should be terminated, or None otherwise.
    Once a termination condition has been reached, it must be reset before it can be used again.

    Termination conditions can be combined using the AND and OR operators.

    Example:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination


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

    component_type = "termination"

    @property
    @abstractmethod
    def terminated(self) -> bool:
        """Check if the termination condition has been reached"""
        ...

    @abstractmethod
    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
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
        return AndTerminationCondition(self, other)

    def __or__(self, other: "TerminationCondition") -> "TerminationCondition":
        """Combine two termination conditions with an OR operation."""
        return OrTerminationCondition(self, other)


class AndTerminationConditionConfig(BaseModel):
    conditions: List[ComponentModel]


class AndTerminationCondition(TerminationCondition, Component[AndTerminationConditionConfig]):
    component_config_schema = AndTerminationConditionConfig
    component_type = "termination"
    component_provider_override = "autogen_agentchat.base.AndTerminationCondition"

    def __init__(self, *conditions: TerminationCondition) -> None:
        self._conditions = conditions
        self._stop_messages: List[StopMessage] = []

    @property
    def terminated(self) -> bool:
        return all(condition.terminated for condition in self._conditions)

    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
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

    def _to_config(self) -> AndTerminationConditionConfig:
        """Convert the AND termination condition to a config."""
        return AndTerminationConditionConfig(conditions=[condition.dump_component() for condition in self._conditions])

    @classmethod
    def _from_config(cls, config: AndTerminationConditionConfig) -> Self:
        """Create an AND termination condition from a config."""
        conditions = [TerminationCondition.load_component(condition_model) for condition_model in config.conditions]
        return cls(*conditions)


class OrTerminationConditionConfig(BaseModel):
    conditions: List[ComponentModel]
    """List of termination conditions where any one being satisfied is sufficient."""


class OrTerminationCondition(TerminationCondition, Component[OrTerminationConditionConfig]):
    component_config_schema = OrTerminationConditionConfig
    component_type = "termination"
    component_provider_override = "autogen_agentchat.base.OrTerminationCondition"

    def __init__(self, *conditions: TerminationCondition) -> None:
        self._conditions = conditions

    @property
    def terminated(self) -> bool:
        return any(condition.terminated for condition in self._conditions)

    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
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

    def _to_config(self) -> OrTerminationConditionConfig:
        """Convert the OR termination condition to a config."""
        return OrTerminationConditionConfig(conditions=[condition.dump_component() for condition in self._conditions])

    @classmethod
    def _from_config(cls, config: OrTerminationConditionConfig) -> Self:
        """Create an OR termination condition from a config."""
        conditions = [TerminationCondition.load_component(condition_model) for condition_model in config.conditions]
        return cls(*conditions)
