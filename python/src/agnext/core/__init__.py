"""
The :mod:`agnext.core` module provides the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
"""

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_props import AgentChildren
from ._agent_proxy import AgentProxy
from ._agent_runtime import AGENT_INSTANTIATION_CONTEXT_VAR, AgentRuntime, agent_instantiation_context
from ._base_agent import BaseAgent
from ._cancellation_token import CancellationToken
from ._serialization import MESSAGE_TYPE_REGISTRY, TypeDeserializer, TypeSerializer

__all__ = [
    "Agent",
    "AgentId",
    "AgentProxy",
    "AgentMetadata",
    "AgentRuntime",
    "BaseAgent",
    "CancellationToken",
    "AgentChildren",
    "agent_instantiation_context",
    "AGENT_INSTANTIATION_CONTEXT_VAR",
    "MESSAGE_TYPE_REGISTRY",
    "TypeSerializer",
    "TypeDeserializer",
]
