from __future__ import annotations

import inspect
import warnings
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Awaitable, Callable, ClassVar, List, Mapping, Tuple, Type, TypeVar, final

from typing_extensions import Self

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._cancellation_token import CancellationToken
from ._message_context import MessageContext
from ._serialization import MessageSerializer, try_get_known_serializers_for_type
from ._subscription import Subscription, UnboundSubscription
from ._subscription_context import SubscriptionInstantiationContext
from ._topic import TopicId
from ._type_prefix_subscription import TypePrefixSubscription

T = TypeVar("T", bound=Agent)

BaseAgentType = TypeVar("BaseAgentType", bound="BaseAgent")


# Decorator for adding an unbound subscription to an agent
def subscription_factory(subscription: UnboundSubscription) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]:
    """:meta private:"""

    def decorator(cls: Type[BaseAgentType]) -> Type[BaseAgentType]:
        cls.internal_unbound_subscriptions_list.append(subscription)
        return cls

    return decorator


def handles(
    type: Type[Any], serializer: MessageSerializer[Any] | List[MessageSerializer[Any]] | None = None
) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]:
    def decorator(cls: Type[BaseAgentType]) -> Type[BaseAgentType]:
        if serializer is None:
            serializer_list = try_get_known_serializers_for_type(type)
        else:
            serializer_list = [serializer] if not isinstance(serializer, Sequence) else serializer

        if len(serializer_list) == 0:
            raise ValueError(f"No serializers found for type {type}. Please provide an explicit serializer.")

        cls.internal_extra_handles_types.append((type, serializer_list))
        return cls

    return decorator


class BaseAgent(ABC, Agent):
    internal_unbound_subscriptions_list: ClassVar[List[UnboundSubscription]] = []
    """:meta private:"""
    internal_extra_handles_types: ClassVar[List[Tuple[Type[Any], List[MessageSerializer[Any]]]]] = []
    """:meta private:"""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Automatically set class_variable in each subclass so that they are not shared between subclasses
        cls.internal_extra_handles_types = []
        cls.internal_unbound_subscriptions_list = []

    @classmethod
    def _handles_types(cls) -> List[Tuple[Type[Any], List[MessageSerializer[Any]]]]:
        return cls.internal_extra_handles_types

    @classmethod
    def _unbound_subscriptions(cls) -> List[UnboundSubscription]:
        return cls.internal_unbound_subscriptions_list

    @property
    def metadata(self) -> AgentMetadata:
        assert self._id is not None
        return AgentMetadata(key=self._id.key, type=self._id.type, description=self._description)

    def __init__(self, description: str) -> None:
        if AgentInstantiationContext.is_in_runtime():
            self._runtime: AgentRuntime = AgentInstantiationContext.current_runtime()
            self._id = AgentInstantiationContext.current_agent_id()
        if not isinstance(description, str):
            raise ValueError("Agent description must be a string")
        self._description = description

    async def init(self, **kwargs: Any) -> None:
        if "runtime" not in kwargs or "agent_id" not in kwargs:
            raise ValueError("Agent must be initialized with runtime and agent_id")
        if not isinstance(kwargs["runtime"], AgentRuntime):
            raise ValueError("Agent must be initialized with runtime of type AgentRuntime")
        if not isinstance(kwargs["agent_id"], AgentId):
            raise ValueError("Agent must be initialized with agent_id of type AgentId")
        self._runtime = kwargs["runtime"]
        self._id = kwargs["agent_id"]

    @property
    def type(self) -> str:
        return self.id.type

    @property
    def id(self) -> AgentId:
        return self._id

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    @final
    async def on_message(self, message: Any, ctx: MessageContext) -> Any:
        return await self.on_message_impl(message, ctx)

    @abstractmethod
    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any: ...

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> Any:
        """See :py:meth:`autogen_core.AgentRuntime.send_message` for more information."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        return await self._runtime.send_message(
            message,
            sender=self.id,
            recipient=recipient,
            cancellation_token=cancellation_token,
            message_id=message_id,
        )

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        await self._runtime.publish_message(message, topic_id, sender=self.id, cancellation_token=cancellation_token)

    async def save_state(self) -> Mapping[str, Any]:
        warnings.warn("save_state not implemented", stacklevel=2)
        return {}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        warnings.warn("load_state not implemented", stacklevel=2)
        pass

    async def close(self) -> None:
        pass

    async def register_instance(
        self,
        runtime: AgentRuntime,
        agent_id: AgentId,
        *,
        skip_class_subscriptions: bool = False,
        skip_direct_message_subscription: bool = False,
    ) -> AgentId:
        agent_id = await runtime.register_agent_instance(agent_instance=self, agent_id=agent_id)
        if not skip_class_subscriptions:
            with SubscriptionInstantiationContext.populate_context(AgentType(agent_id.type)):
                subscriptions: List[Subscription] = []
                for unbound_subscription in self._unbound_subscriptions():
                    subscriptions_list_result = unbound_subscription()
                    if inspect.isawaitable(subscriptions_list_result):
                        subscriptions_list = await subscriptions_list_result
                    else:
                        subscriptions_list = subscriptions_list_result

                    subscriptions.extend(subscriptions_list)
            try:
                for subscription in subscriptions:
                    await runtime.add_subscription(subscription)
            except ValueError:
                # We don't care if the subscription already exists
                pass

        if not skip_direct_message_subscription:
            # Additionally adds a special prefix subscription for this agent to receive direct messages
            try:
                await runtime.add_subscription(
                    TypePrefixSubscription(
                        # The prefix MUST include ":" to avoid collisions with other agents
                        topic_type_prefix=agent_id.type + ":",
                        agent_type=agent_id.type,
                    )
                )
            except ValueError:
                # We don't care if the subscription already exists
                pass

        # TODO: deduplication
        for _message_type, serializer in self._handles_types():
            runtime.add_message_serializer(serializer)

        return agent_id

    @classmethod
    async def register(
        cls,
        runtime: AgentRuntime,
        type: str,
        factory: Callable[[], Self | Awaitable[Self]],
        *,
        skip_class_subscriptions: bool = False,
        skip_direct_message_subscription: bool = False,
    ) -> AgentType:
        agent_type = AgentType(type)
        agent_type = await runtime.register_factory(type=agent_type, agent_factory=factory, expected_class=cls)
        if not skip_class_subscriptions:
            with SubscriptionInstantiationContext.populate_context(agent_type):
                subscriptions: List[Subscription] = []
                for unbound_subscription in cls._unbound_subscriptions():
                    subscriptions_list_result = unbound_subscription()
                    if inspect.isawaitable(subscriptions_list_result):
                        subscriptions_list = await subscriptions_list_result
                    else:
                        subscriptions_list = subscriptions_list_result

                    subscriptions.extend(subscriptions_list)
            for subscription in subscriptions:
                await runtime.add_subscription(subscription)

        if not skip_direct_message_subscription:
            # Additionally adds a special prefix subscription for this agent to receive direct messages
            await runtime.add_subscription(
                TypePrefixSubscription(
                    # The prefix MUST include ":" to avoid collisions with other agents
                    topic_type_prefix=agent_type.type + ":",
                    agent_type=agent_type.type,
                )
            )

        # TODO: deduplication
        for _message_type, serializer in cls._handles_types():
            runtime.add_message_serializer(serializer)

        return agent_type
