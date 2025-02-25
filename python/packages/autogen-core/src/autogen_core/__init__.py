import importlib.metadata

__version__ = importlib.metadata.version("autogen_core")

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_proxy import AgentProxy
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._base_agent import BaseAgent
from ._cache_store import CacheStore, InMemoryStore
from ._cancellation_token import CancellationToken
from ._closure_agent import ClosureAgent, ClosureContext
from ._component_config import (
    Component,
    ComponentBase,
    ComponentFromConfig,
    ComponentLoader,
    ComponentModel,
    ComponentSchemaType,
    ComponentToConfig,
    ComponentType,
    is_component_class,
    is_component_instance,
)
from ._constants import (
    EVENT_LOGGER_NAME as EVENT_LOGGER_NAME_ALIAS,
)
from ._constants import (
    ROOT_LOGGER_NAME as ROOT_LOGGER_NAME_ALIAS,
)
from ._constants import (
    TRACE_LOGGER_NAME as TRACE_LOGGER_NAME_ALIAS,
)
from ._default_subscription import DefaultSubscription, default_subscription, type_subscription
from ._default_topic import DefaultTopicId
from ._image import Image
from ._intervention import (
    DefaultInterventionHandler,
    DropMessage,
    InterventionHandler,
)
from ._message_context import MessageContext
from ._message_handler_context import MessageHandlerContext
from ._routed_agent import RoutedAgent, event, message_handler, rpc
from ._serialization import (
    JSON_DATA_CONTENT_TYPE as JSON_DATA_CONTENT_TYPE_ALIAS,
)
from ._serialization import (
    PROTOBUF_DATA_CONTENT_TYPE as PROTOBUF_DATA_CONTENT_TYPE_ALIAS,
)
from ._serialization import (
    MessageSerializer,
    UnknownPayload,
    try_get_known_serializers_for_type,
)
from ._single_threaded_agent_runtime import SingleThreadedAgentRuntime
from ._subscription import Subscription
from ._subscription_context import SubscriptionInstantiationContext
from ._topic import TopicId
from ._type_prefix_subscription import TypePrefixSubscription
from ._type_subscription import TypeSubscription
from ._types import FunctionCall

EVENT_LOGGER_NAME = EVENT_LOGGER_NAME_ALIAS
"""The name of the logger used for structured events."""

ROOT_LOGGER_NAME = ROOT_LOGGER_NAME_ALIAS
"""The name of the root logger."""

TRACE_LOGGER_NAME = TRACE_LOGGER_NAME_ALIAS
"""Logger name used for developer intended trace logging. The content and format of this log should not be depended upon."""

JSON_DATA_CONTENT_TYPE = JSON_DATA_CONTENT_TYPE_ALIAS
"""The content type for JSON data."""

PROTOBUF_DATA_CONTENT_TYPE = PROTOBUF_DATA_CONTENT_TYPE_ALIAS
"""The content type for Protobuf data."""

__all__ = [
    "Agent",
    "AgentId",
    "AgentProxy",
    "AgentMetadata",
    "AgentRuntime",
    "BaseAgent",
    "CacheStore",
    "InMemoryStore",
    "CancellationToken",
    "AgentInstantiationContext",
    "TopicId",
    "Subscription",
    "MessageContext",
    "AgentType",
    "SubscriptionInstantiationContext",
    "MessageHandlerContext",
    "MessageSerializer",
    "try_get_known_serializers_for_type",
    "UnknownPayload",
    "Image",
    "RoutedAgent",
    "ClosureAgent",
    "ClosureContext",
    "message_handler",
    "event",
    "rpc",
    "FunctionCall",
    "TypeSubscription",
    "DefaultSubscription",
    "DefaultTopicId",
    "default_subscription",
    "type_subscription",
    "TypePrefixSubscription",
    "JSON_DATA_CONTENT_TYPE",
    "PROTOBUF_DATA_CONTENT_TYPE",
    "SingleThreadedAgentRuntime",
    "ROOT_LOGGER_NAME",
    "EVENT_LOGGER_NAME",
    "TRACE_LOGGER_NAME",
    "Component",
    "ComponentBase",
    "ComponentFromConfig",
    "ComponentLoader",
    "ComponentModel",
    "ComponentSchemaType",
    "ComponentToConfig",
    "ComponentType",
    "is_component_class",
    "is_component_instance",
    "DropMessage",
    "InterventionHandler",
    "DefaultInterventionHandler",
]
