import asyncio
from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel
from typing_extensions import Self

from autogen_core import Component, ComponentBase, ComponentModel

from ...models import LLMMessage
from ._types import TriggerMessage


class MessageCompletionException(BaseException): ...


class MessageCompletionCondition(ABC, ComponentBase[BaseModel]):
    component_type = "message_completion_condition"

    @property
    @abstractmethod
    def triggered(self) -> bool:
        """Check if the termination condition has been reached"""
        ...

    @abstractmethod
    async def __call__(self, messages: List[LLMMessage]) -> TriggerMessage | None: ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the model completion condition."""
        ...

    def __and__(self, other: "MessageCompletionCondition") -> "MessageCompletionCondition":
        """Combine two termination conditions with an AND operation."""
        return AndMessageCompletionCondition(self, other)

    def __or__(self, other: "MessageCompletionCondition") -> "MessageCompletionCondition":
        """Combine two termination conditions with an OR operation."""
        return OrMessageCompletionCondition(self, other)


class AndMessageCompletionConditionConfig(BaseModel):
    conditions: List[ComponentModel]


class AndMessageCompletionCondition(MessageCompletionCondition, Component[AndMessageCompletionConditionConfig]):
    component_config_schema = AndMessageCompletionConditionConfig
    component_type = "trigger"
    component_provider_override = "autogen_core.model_context.AndMessageCompletionCondition"

    def __init__(self, *conditions: MessageCompletionCondition) -> None:
        self._conditions = conditions
        self._trigger_messages: List[TriggerMessage] = []

    @property
    def triggered(self) -> bool:
        return all(condition.triggered for condition in self._conditions)

    async def __call__(self, messages: List[LLMMessage]) -> TriggerMessage | None:
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
        # source = ", ".join(trigger_message.source for trigger_message in self._trigger_messages)
        return TriggerMessage(content=content)

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()
        self._trigger_messages.clear()

    def _to_config(self) -> AndMessageCompletionConditionConfig:
        """Convert the AND termination condition to a config."""
        return AndMessageCompletionConditionConfig(
            conditions=[condition.dump_component() for condition in self._conditions]
        )

    @classmethod
    def _from_config(cls, config: AndMessageCompletionConditionConfig) -> Self:
        """Create an AND termination condition from a config."""
        conditions = [
            MessageCompletionCondition.load_component(condition_model) for condition_model in config.conditions
        ]
        return cls(*conditions)


class OrMessageCompletionConditionConfig(BaseModel):
    conditions: List[ComponentModel]
    """List of termination conditions where any one being satisfied is sufficient."""


class OrMessageCompletionCondition(MessageCompletionCondition, Component[OrMessageCompletionConditionConfig]):
    component_config_schema = OrMessageCompletionConditionConfig
    component_type = "termination"
    component_provider_override = "autogen_agentchat.base.OrTerminationCondition"

    def __init__(self, *conditions: MessageCompletionCondition) -> None:
        self._conditions = conditions

    @property
    def triggered(self) -> bool:
        return any(condition.triggered for condition in self._conditions)

    async def __call__(self, messages: List[LLMMessage]) -> TriggerMessage | None:
        if self.triggered:
            raise RuntimeError("Termination condition has already been reached")
        trigger_messages = await asyncio.gather(*[condition(messages) for condition in self._conditions])
        trigger_messages_filter = [
            trigger_message for trigger_message in trigger_messages if trigger_message is not None
        ]
        if len(trigger_messages_filter) > 0:
            content = ", ".join(trigger_message.content for trigger_message in trigger_messages_filter)
            # source = ", ".join(trigger_message.source for stop_message in stop_messages_filter)
            return TriggerMessage(content=content)
        return None

    async def reset(self) -> None:
        for condition in self._conditions:
            await condition.reset()

    def _to_config(self) -> OrMessageCompletionConditionConfig:
        """Convert the OR termination condition to a config."""
        return OrMessageCompletionConditionConfig(
            conditions=[condition.dump_component() for condition in self._conditions]
        )

    @classmethod
    def _from_config(cls, config: OrMessageCompletionConditionConfig) -> Self:
        """Create an OR termination condition from a config."""
        conditions = [
            MessageCompletionCondition.load_component(condition_model) for condition_model in config.conditions
        ]
        return cls(*conditions)
