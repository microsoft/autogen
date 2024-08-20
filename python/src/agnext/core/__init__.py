"""
The :mod:`agnext.core` module provides the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
"""

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_props import AgentChildren
from ._agent_proxy import AgentProxy
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._base_agent import BaseAgent
from ._cancellation_token import CancellationToken
from ._message_context import MessageContext
from ._serialization import MESSAGE_TYPE_REGISTRY, Serialization, TypeDeserializer, TypeSerializer
from ._subscription import Subscription
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
    "MESSAGE_TYPE_REGISTRY",
    "TypeSerializer",
    "TypeDeserializer",
    "TopicId",
    "Subscription",
    "MessageContext",
    "Serialization",
    "AgentType",
]
