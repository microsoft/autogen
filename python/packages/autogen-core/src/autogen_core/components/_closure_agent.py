from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, List, Mapping, Protocol, Sequence, TypeVar, get_type_hints

from autogen_core.base._serialization import try_get_known_serializers_for_type
from autogen_core.base._subscription_context import SubscriptionInstantiationContext

from ..base import (
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentRuntime,
    AgentType,
    BaseAgent,
    CancellationToken,
    MessageContext,
    Subscription,
    TopicId,
)
from ..base._type_helpers import get_types
from ..base.exceptions import CantHandleException

T = TypeVar("T")
ClosureAgentType = TypeVar("ClosureAgentType", bound="ClosureAgent")


def get_handled_types_from_closure(
    closure: Callable[[ClosureAgent, T, MessageContext], Awaitable[Any]],
) -> Sequence[type]:
    args = inspect.getfullargspec(closure)[0]
    if len(args) != 3:
        raise AssertionError("Closure must have 4 arguments")

    message_arg_name = args[1]

    type_hints = get_type_hints(closure)

    if "return" not in type_hints:
        raise AssertionError("return not found in function signature")

    # Get the type of the message parameter
    target_types = get_types(type_hints[message_arg_name])
    if target_types is None:
        raise AssertionError("Message type not found")

    # print(type_hints)
    return_types = get_types(type_hints["return"])

    if return_types is None:
        raise AssertionError("Return type not found")

    return target_types


class ClosureContext(Protocol):
    @property
    def id(self) -> AgentId: ...

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Any: ...

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> None: ...


class ClosureAgent(BaseAgent, ClosureContext):
    def __init__(
        self, description: str, closure: Callable[[ClosureContext, T, MessageContext], Awaitable[Any]]
    ) -> None:
        try:
            runtime = AgentInstantiationContext.current_runtime()
            id = AgentInstantiationContext.current_agent_id()
        except Exception as e:
            raise RuntimeError(
                "ClosureAgent must be instantiated within the context of an AgentRuntime. It cannot be directly instantiated."
            ) from e

        self._runtime: AgentRuntime = runtime
        self._id: AgentId = id
        self._description = description
        handled_types = get_handled_types_from_closure(closure)
        self._expected_types = handled_types
        self._closure = closure
        super().__init__(description)

    @property
    def metadata(self) -> AgentMetadata:
        assert self._id is not None
        return AgentMetadata(
            key=self._id.key,
            type=self._id.type,
            description=self._description,
        )

    @property
    def id(self) -> AgentId:
        return self._id

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        if type(message) not in self._expected_types:
            raise CantHandleException(
                f"Message type {type(message)} not in target types {self._expected_types} of {self.id}"
            )
        return await self._closure(self, message, ctx)

    async def save_state(self) -> Mapping[str, Any]:
        raise ValueError("save_state not implemented for ClosureAgent")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        raise ValueError("load_state not implemented for ClosureAgent")

    @classmethod
    async def register_closure(
        cls,
        runtime: AgentRuntime,
        type: str,
        closure: Callable[[ClosureContext, T, MessageContext], Awaitable[Any]],
        *,
        skip_class_subscriptions: bool = False,
        skip_direct_message_subscription: bool = False,
        description: str = "",
        subscriptions: Callable[[], list[Subscription] | Awaitable[list[Subscription]]] | None = None,
    ) -> AgentType:
        def factory() -> ClosureAgent:
            return ClosureAgent(description=description, closure=closure)

        agent_type = await cls.register(
            runtime=runtime,
            type=type,
            factory=factory,  # type: ignore
            skip_class_subscriptions=skip_class_subscriptions,
            skip_direct_message_subscription=skip_direct_message_subscription,
        )

        subscriptions_list: List[Subscription] = []
        if subscriptions is not None:
            with SubscriptionInstantiationContext.populate_context(agent_type):
                subscriptions_list_result = subscriptions()
                if inspect.isawaitable(subscriptions_list_result):
                    subscriptions_list.extend(await subscriptions_list_result)
                else:
                    # just ignore mypy here
                    subscriptions_list.extend(subscriptions_list_result)  # type: ignore

        for subscription in subscriptions_list:
            await runtime.add_subscription(subscription)

        handled_types = get_handled_types_from_closure(closure)
        for message_type in handled_types:
            # TODO: support custom serializers
            serializer = try_get_known_serializers_for_type(message_type)
            runtime.add_message_serializer(serializer)

        return agent_type
