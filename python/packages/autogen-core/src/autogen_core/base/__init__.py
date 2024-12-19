"""
The :mod:`autogen_core.base` module provides the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
"""

from typing import Any, TypeVar

from typing_extensions import deprecated

from .._agent import Agent as AgentAlias
from .._agent_id import AgentId as AgentIdAlias
from .._agent_instantiation import AgentInstantiationContext as AgentInstantiationContextAlias
from .._agent_metadata import AgentMetadata as AgentMetadataAlias
from .._agent_proxy import AgentProxy as AgentProxyAlias
from .._agent_runtime import AgentRuntime as AgentRuntimeAlias
from .._agent_type import AgentType as AgentTypeAlias
from .._base_agent import BaseAgent as BaseAgentAlias
from .._cancellation_token import CancellationToken as CancellationTokenAlias
from .._message_context import MessageContext as MessageContextAlias
from .._message_handler_context import MessageHandlerContext as MessageHandlerContextAlias
from .._serialization import (
    MessageSerializer as MessageSerializerAlias,
)
from .._serialization import (
    UnknownPayload as UnknownPayloadAlias,
)
from .._serialization import (
    try_get_known_serializers_for_type as try_get_known_serializers_for_type_alias,
)
from .._subscription import Subscription as SubscriptionAlias
from .._subscription_context import SubscriptionInstantiationContext as SubscriptionInstantiationContextAlias
from .._topic import TopicId as TopicIdAlias


@deprecated("autogen_core.base.Agent moved to autogen_core.Agent. This alias will be removed in 0.4.0.")
class Agent(AgentAlias):
    pass


@deprecated("autogen_core.base.AgentId moved to autogen_core.AgentId. This alias will be removed in 0.4.0.")
class AgentId(AgentIdAlias):
    pass


@deprecated(
    "autogen_core.base.AgentInstantiationContext moved to autogen_core.AgentInstantiationContext. This alias will be removed in 0.4.0."
)
class AgentInstantiationContext(AgentInstantiationContextAlias):
    pass


@deprecated("autogen_core.base.AgentMetadata moved to autogen_core.AgentMetadata. This alias will be removed in 0.4.0.")
class AgentMetadata(AgentMetadataAlias):
    pass


@deprecated("autogen_core.base.AgentProxy moved to autogen_core.AgentProxy. This alias will be removed in 0.4.0.")
class AgentProxy(AgentProxyAlias):
    pass


@deprecated("autogen_core.base.AgentRuntime moved to autogen_core.AgentRuntime. This alias will be removed in 0.4.0.")
class AgentRuntime(AgentRuntimeAlias):
    pass


@deprecated("autogen_core.base.AgentType moved to autogen_core.AgentType. This alias will be removed in 0.4.0.")
class AgentType(AgentTypeAlias):
    pass


@deprecated("autogen_core.base.BaseAgent moved to autogen_core.BaseAgent. This alias will be removed in 0.4.0.")
class BaseAgent(BaseAgentAlias):
    pass


@deprecated(
    "autogen_core.base.CancellationToken moved to autogen_core.CancellationToken. This alias will be removed in 0.4.0."
)
class CancellationToken(CancellationTokenAlias):
    pass


@deprecated(
    "autogen_core.base.MessageContext moved to autogen_core.MessageContext. This alias will be removed in 0.4.0."
)
class MessageContext(MessageContextAlias):
    pass


@deprecated(
    "autogen_core.base.MessageHandlerContext moved to autogen_core.MessageHandlerContext. This alias will be removed in 0.4.0."
)
class MessageHandlerContext(MessageHandlerContextAlias):
    pass


@deprecated(
    "autogen_core.base.UnknownPayloadAlias moved to autogen_core.UnknownPayloadAlias. This alias will be removed in 0.4.0."
)
class UnknownPayload(UnknownPayloadAlias):
    pass


T = TypeVar("T")


@deprecated(
    "autogen_core.base.MessageSerializer moved to autogen_core.MessageSerializer. This alias will be removed in 0.4.0."
)
class MessageSerializer(MessageSerializerAlias[T]):
    pass


@deprecated("autogen_core.base.Subscription moved to autogen_core.Subscription. This alias will be removed in 0.4.0.")
class Subscription(SubscriptionAlias):
    pass


@deprecated(
    "autogen_core.base.try_get_known_serializers_for_type moved to autogen_core.try_get_known_serializers_for_type. This alias will be removed in 0.4.0."
)
def try_get_known_serializers_for_type(cls: type[Any]) -> list[MessageSerializerAlias[Any]]:
    return try_get_known_serializers_for_type_alias(cls)


@deprecated(
    "autogen_core.base.SubscriptionInstantiationContext moved to autogen_core.SubscriptionInstantiationContext. This alias will be removed in 0.4.0."
)
class SubscriptionInstantiationContext(SubscriptionInstantiationContextAlias):
    pass


@deprecated("autogen_core.base.TopicId moved to autogen_core.TopicId. This alias will be removed in 0.4.0.")
class TopicId(TopicIdAlias):
    pass


__all__ = []  # type: ignore
