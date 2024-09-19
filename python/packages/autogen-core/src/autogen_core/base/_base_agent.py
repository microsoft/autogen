from __future__ import annotations

import inspect
import warnings
from abc import ABC, abstractmethod
from collections.abc import Sequence
from re import S
from typing import Any, Awaitable, Callable, ClassVar, List, Mapping, Tuple, Type, TypeVar, overload

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
from ._subscription import UnboundSubscription
from ._subscription_context import SubscriptionInstantiationContext
from ._topic import TopicId

T = TypeVar("T", bound=Agent)

BaseAgentType = TypeVar("BaseAgentType", bound="BaseAgent")


# Decorator for adding an unbound subscription to an agent
def subscription_factory(subscription: UnboundSubscription) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]:
    def decorator(cls: Type[BaseAgentType]) -> Type[BaseAgentType]:
        cls._unbound_subscriptions_list.append(subscription)
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

        cls._extra_handles_types.append((type, serializer_list))
        return cls

    return decorator


class BaseAgent(ABC, Agent):
    _unbound_subscriptions_list: ClassVar[List[UnboundSubscription]] = []
    _extra_handles_types: ClassVar[List[Tuple[Type[Any], List[MessageSerializer[Any]]]]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Automatically set class_variable in each subclass so that they are not shared between subclasses
        cls._extra_handles_types = []
        cls._unbound_subscriptions_list = []

    @classmethod
    def _handles_types(cls) -> List[Tuple[Type[Any], List[MessageSerializer[Any]]]]:
        return cls._extra_handles_types

    @classmethod
    def _unbound_subscriptions(cls) -> List[UnboundSubscription]:
        return cls._unbound_subscriptions_list

    @property
    def metadata(self) -> AgentMetadata:
        assert self._id is not None
        return AgentMetadata(key=self._id.key, type=self._id.type, description=self._description)

    def __init__(self, description: str) -> None:
        try:
            runtime = AgentInstantiationContext.current_runtime()
            id = AgentInstantiationContext.current_agent_id()
        except LookupError as e:
            raise RuntimeError(
                "BaseAgent must be instantiated within the context of an AgentRuntime. It cannot be directly instantiated."
            ) from e

        self._runtime: AgentRuntime = runtime
        self._id: AgentId = id
        if not isinstance(description, str):
            raise ValueError("Agent description must be a string")
        self._description = description

    @property
    def type(self) -> str:
        return self.id.type

    @property
    def id(self) -> AgentId:
        return self._id

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    @abstractmethod
    async def on_message(self, message: Any, ctx: MessageContext) -> Any: ...

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Any:
        """See :py:meth:`autogen_core.base.AgentRuntime.send_message` for more information."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        return await self._runtime.send_message(
            message,
            sender=self.id,
            recipient=recipient,
            cancellation_token=cancellation_token,
        )

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        await self._runtime.publish_message(message, topic_id, sender=self.id, cancellation_token=cancellation_token)

    def save_state(self) -> Mapping[str, Any]:
        warnings.warn("save_state not implemented", stacklevel=2)
        return {}

    def load_state(self, state: Mapping[str, Any]) -> None:
        warnings.warn("load_state not implemented", stacklevel=2)
        pass

    @classmethod
    async def register(
        cls,
        runtime: AgentRuntime,
        type: str,
        factory: Callable[[], Self | Awaitable[Self]],
        *,
        skip_class_subscriptions: bool = False,
    ) -> AgentType:
        agent_type = AgentType(type)
        agent_type = await runtime.register_factory(type=agent_type, agent_factory=factory, expected_class=cls)
        if not skip_class_subscriptions:
            with SubscriptionInstantiationContext.populate_context(agent_type):
                subscriptions = []
                for unbound_subscription in cls._unbound_subscriptions():
                    subscriptions_list_result = unbound_subscription()
                    if inspect.isawaitable(subscriptions_list_result):
                        subscriptions_list = await subscriptions_list_result
                    else:
                        subscriptions_list = subscriptions_list_result

                    subscriptions.extend(subscriptions_list)
            for subscription in subscriptions:
                await runtime.add_subscription(subscription)

        # TODO: deduplication
        for _message_type, serializer in cls._handles_types():
            runtime.add_message_serializer(serializer)

        return agent_type
