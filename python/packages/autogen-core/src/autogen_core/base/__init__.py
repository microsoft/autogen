"""
The :mod:`autogen_core.base` module provides the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
"""

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_props import AgentChildren
from ._agent_proxy import AgentProxy
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._base_agent import BaseAgent, subscription_factory
from ._cancellation_token import CancellationToken
from ._message_context import MessageContext
from ._message_handler_context import MessageHandlerContext
from ._serialization import (
    JSON_DATA_CONTENT_TYPE,
    PROTOBUF_DATA_CONTENT_TYPE,
    MessageSerializer,
    SerializationRegistry,
    UnknownPayload,
    try_get_known_serializers_for_type,
)
from ._subscription import Subscription
from ._subscription_context import SubscriptionInstantiationContext
from ._topic import TopicId

__all__ = [
    "Agent",
    "AgentId",
    "AgentProxy",
    "AgentMetadata",
    "AgentRuntime",
    "BaseAgent",
    "CancellationToken",
    "AgentChildren",
    "AgentInstantiationContext",
    "TopicId",
    "Subscription",
    "MessageContext",
    "SerializationRegistry",
    "AgentType",
    "SubscriptionInstantiationContext",
    "MessageHandlerContext",
    "JSON_DATA_CONTENT_TYPE",
    "PROTOBUF_DATA_CONTENT_TYPE",
    "MessageSerializer",
    "try_get_known_serializers_for_type",
    "UnknownPayload",
    "subscription_factory",
]
