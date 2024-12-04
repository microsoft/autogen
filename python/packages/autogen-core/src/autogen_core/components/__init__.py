"""
The :mod:`autogen_core.components` module provides building blocks for creating single agents
"""

from typing import Any, Callable, Type, TypeVar

from typing_extensions import deprecated

from .._base_agent import BaseAgent
from .._closure_agent import ClosureAgent as ClosureAgentAlias
from .._closure_agent import ClosureContext as ClosureContextAlias
from .._default_subscription import (
    DefaultSubscription as DefaultSubscriptionAlias,
)
from .._default_subscription import (
    default_subscription as default_subscription_alias,
)
from .._default_subscription import (
    type_subscription as type_subscription_alias,
)
from .._default_topic import DefaultTopicId as DefaultTopicIdAlias
from .._image import Image as ImageAlias
from .._routed_agent import (
    RoutedAgent as RoutedAgentAlias,
)
from .._routed_agent import (
    event as event_alias,
)
from .._routed_agent import (
    message_handler as message_handler_alias,
)
from .._routed_agent import (
    rpc as rpc_aliass,
)
from .._type_prefix_subscription import TypePrefixSubscription as TypePrefixSubscriptionAlias
from .._type_subscription import TypeSubscription as TypeSubscriptionAlias
from .._types import FunctionCall as FunctionCallAlias

__all__ = []  # type: ignore


@deprecated("Moved to autogen_core.TypePrefixSubscription. Will be removed in 0.4.0")
class TypePrefixSubscription(TypePrefixSubscriptionAlias):
    pass


@deprecated("Moved to autogen_core.TypeSubscription. Will be removed in 0.4.0")
class TypeSubscription(TypeSubscriptionAlias):
    pass


@deprecated("Moved to autogen_core.ClosureAgent. Will be removed in 0.4.0")
class ClosureAgent(ClosureAgentAlias):
    pass


@deprecated("Moved to autogen_core.ClosureContext. Will be removed in 0.4.0")
class ClosureContext(ClosureContextAlias):
    pass


@deprecated("Moved to autogen_core.DefaultSubscription. Will be removed in 0.4.0")
class DefaultSubscription(DefaultSubscriptionAlias):
    pass


BaseAgentType = TypeVar("BaseAgentType", bound="BaseAgent")


@deprecated("Moved to autogen_core.default_subscription. Will be removed in 0.4.0")
def default_subscription(
    cls: Type[BaseAgentType] | None = None,
) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]] | Type[BaseAgentType]:
    return default_subscription_alias(cls)  # type: ignore


@deprecated("Moved to autogen_core.type_subscription. Will be removed in 0.4.0")
def type_subscription(topic_type: str) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]:
    return type_subscription_alias(topic_type)


@deprecated("Moved to autogen_core.DefaultTopicId. Will be removed in 0.4.0")
class DefaultTopicId(DefaultTopicIdAlias):
    pass


@deprecated("Moved to autogen_core.Image. Will be removed in 0.4.0")
class Image(ImageAlias):
    pass


@deprecated("Moved to autogen_core.RoutedAgent. Will be removed in 0.4.0")
class RoutedAgent(RoutedAgentAlias):
    pass


# Generic forwarding of all args to the alias
@deprecated("Moved to autogen_core.event. Will be removed in 0.4.0")
def event(*args: Any, **kwargs: Any) -> Any:
    return event_alias(*args, **kwargs)  # type: ignore


@deprecated("Moved to autogen_core.message_handler. Will be removed in 0.4.0")
def message_handler(*args: Any, **kwargs: Any) -> Any:
    return message_handler_alias(*args, **kwargs)  # type: ignore


@deprecated("Moved to autogen_core.rpc. Will be removed in 0.4.0")
def rpc(*args: Any, **kwargs: Any) -> Any:
    return rpc_aliass(*args, **kwargs)  # type: ignore


@deprecated("Moved to autogen_core.FunctionCall. Will be removed in 0.4.0")
class FunctionCall(FunctionCallAlias):
    pass
