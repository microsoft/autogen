import asyncio
from abc import ABC, abstractmethod
from typing import List, Sequence

from pydantic import BaseModel
from typing_extensions import Self

from autogen_core import Component, ComponentBase, ComponentModel

from .._types import ContextMessage, TriggerMessage


class MessageCompletionException(BaseException): ...


class MessageCompletionCondition(ABC, ComponentBase[BaseModel]):
    """A stateful condition that determines when a message completion should be triggered.
    A message completion condition is a callable that takes a sequence of ContextMessage objects
    since the last time the condition was called, and returns a TriggerMessage if the
    conversation should be terminated, or None otherwise.
    Once a message completion condition has been reached, it must be reset before it can be used again.
    Message completion conditions can be combined using the AND and OR operators.
    Example:
        .. code-block:: python
            import asyncio
            from autogen_core.model_context.conditions import (
                MaxMessageCompletion,
                TextMentionMessageCompletion,
            )


            async def main() -> None:
                # Terminate the conversation after 10 turns or if the text "SUMMARY" is mentioned.
                cond1 = MaxMessageCompletion(10) | TextMentionMessageCompletion("SUMMARY")
                # Terminate the conversation after 10 turns and if the text "SUMMARY" is mentioned.
                cond2 = MaxMessageCompletion(10) & TextMentionMessageCompletion("SUMMARY")
                # ...
                # Reset the message completion condition.
                await cond1.reset()
                await cond2.reset()


            asyncio.run(main())
    """

    component_type = "message_completion_condition"

    @property
    @abstractmethod
    def triggered(self) -> bool:
        """Check if the trigger condition has been reached"""
        ...

    @abstractmethod
    async def __call__(self, messages: Sequence[ContextMessage]) -> TriggerMessage | None:
        """Check if the message completion should be triggered based on the messages received since the last call.

        Args:
            messages (Sequence[ContextMessage]): The messages received since the last call.
        Returns:
            TriggerMessage | None: The trigger message if the condition is met, or None if not.
        Raises:
            MessageCompletionException: If the message completion condition has already been reached."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the model completion condition."""
        ...

    def __and__(self, other: "MessageCompletionCondition") -> "MessageCompletionCondition":
        """Combine two trigger conditions with an AND operation."""
        return AndMessageCompletionCondition(self, other)

    def __or__(self, other: "MessageCompletionCondition") -> "MessageCompletionCondition":
        """Combine two trigger conditions with an OR operation."""
        return OrMessageCompletionCondition(self, other)


class AndMessageCompletionConditionConfig(BaseModel):
    conditions: List[ComponentModel]


class AndMessageCompletionCondition(MessageCompletionCondition, Component[AndMessageCompletionConditionConfig]):
    component_config_schema = AndMessageCompletionConditionConfig
    component_type = "trigger"
    component_provider_override = "autogen_core.model_context.conditions.AndMessageCompletionCondition"

    def __init__(self, *conditions: MessageCompletionCondition) -> None:
        self._conditions = conditions
        self._trigger_messages: List[TriggerMessage] = []

    @property
    def triggered(self) -> bool:
        return all(condition.triggered for condition in self._conditions)

    async def __call__(self, messages: Sequence[ContextMessage]) -> TriggerMessage | None:
        if self.triggered:
            raise MessageCompletionException("Message completion condition has already been reached.")
        # Check all remaining conditions.
        trigger_messages = await asyncio.gather(
            *[condition(messages) for condition in self._conditions if not condition.triggered]
        )
        # Collect stop messages.
        for trigger_message in trigger_messages:
            if trigger_message is not None:
                self._trigger_messages.append(trigger_message)
        if any(trigger_message is None for trigger_message in trigger_messages):
            # If any remaining condition has not reached termination, it is not terminated.
            return None
        content = ", ".join(trigger_message.content for trigger_message in self._trigger_messages)
        source = ", ".join(trigger_message.source for trigger_message in self._trigger_messages)
        return TriggerMessage(content=content, source=source)

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()
        self._trigger_messages.clear()

    def _to_config(self) -> AndMessageCompletionConditionConfig:
        """Convert the AND trigger condition to a config."""
        return AndMessageCompletionConditionConfig(
            conditions=[condition.dump_component() for condition in self._conditions]
        )

    @classmethod
    def _from_config(cls, config: AndMessageCompletionConditionConfig) -> Self:
        """Create an AND trigger condition from a config."""
        conditions = [
            MessageCompletionCondition.load_component(condition_model) for condition_model in config.conditions
        ]
        return cls(*conditions)


class OrMessageCompletionConditionConfig(BaseModel):
    conditions: List[ComponentModel]
    """List of termination conditions where any one being satisfied is sufficient."""


class OrMessageCompletionCondition(MessageCompletionCondition, Component[OrMessageCompletionConditionConfig]):
    component_config_schema = OrMessageCompletionConditionConfig
    component_type = "trigger"
    component_provider_override = "autogen_core.model_context.conditions.OrTerminationCondition"

    def __init__(self, *conditions: MessageCompletionCondition) -> None:
        self._conditions = conditions

    @property
    def triggered(self) -> bool:
        return any(condition.triggered for condition in self._conditions)

    async def __call__(self, messages: Sequence[ContextMessage]) -> TriggerMessage | None:
        if self.triggered:
            raise RuntimeError("Message completion condition has already been reached")
        trigger_messages = await asyncio.gather(*[condition(messages) for condition in self._conditions])
        trigger_messages_filter = [
            trigger_message for trigger_message in trigger_messages if trigger_message is not None
        ]
        if len(trigger_messages_filter) > 0:
            content = ", ".join(trigger_message.content for trigger_message in trigger_messages_filter)
            source = ", ".join(trigger_message.source for trigger_message in trigger_messages_filter)
            return TriggerMessage(content=content, source=source)
        return None

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()

    def _to_config(self) -> OrMessageCompletionConditionConfig:
        """Convert the OR trigger condition to a config."""
        return OrMessageCompletionConditionConfig(
            conditions=[condition.dump_component() for condition in self._conditions]
        )

    @classmethod
    def _from_config(cls, config: OrMessageCompletionConditionConfig) -> Self:
        """Create an OR trigger condition from a config."""
        conditions = [
            MessageCompletionCondition.load_component(condition_model) for condition_model in config.conditions
        ]
        return cls(*conditions)
