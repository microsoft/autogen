import inspect
from typing import Any, Awaitable, Callable, List, Mapping, Sequence, TypeVar, get_type_hints

from ..base import (
    Agent,
    AgentId,
    AgentInstantiationContext,
    AgentMetadata,
    AgentRuntime,
    AgentType,
    MessageContext,
    Subscription,
    SubscriptionInstantiationContext,
    try_get_known_serializers_for_type,
)
from ..base._type_helpers import get_types
from ..base.exceptions import CantHandleException

T = TypeVar("T")


def get_handled_types_from_closure(
    closure: Callable[[AgentRuntime, AgentId, T, MessageContext], Awaitable[Any]],
) -> Sequence[type]:
    args = inspect.getfullargspec(closure)[0]
    if len(args) != 4:
        raise AssertionError("Closure must have 4 arguments")

    message_arg_name = args[2]

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


class ClosureAgent(Agent):
    def __init__(
        self, description: str, closure: Callable[[AgentRuntime, AgentId, T, MessageContext], Awaitable[Any]]
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

    async def on_message(self, message: Any, ctx: MessageContext) -> Any:
        if type(message) not in self._expected_types:
            raise CantHandleException(
                f"Message type {type(message)} not in target types {self._expected_types} of {self.id}"
            )
        return await self._closure(self._runtime, self._id, message, ctx)

    async def save_state(self) -> Mapping[str, Any]:
        raise ValueError("save_state not implemented for ClosureAgent")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        raise ValueError("load_state not implemented for ClosureAgent")

    @classmethod
    async def register(
        cls,
        runtime: AgentRuntime,
        type: str,
        closure: Callable[[AgentRuntime, AgentId, T, MessageContext], Awaitable[Any]],
        *,
        description: str = "",
        subscriptions: Callable[[], list[Subscription] | Awaitable[list[Subscription]]] | None = None,
    ) -> AgentType:
        agent_type = AgentType(type)
        subscriptions_list: List[Subscription] = []
        if subscriptions is not None:
            with SubscriptionInstantiationContext.populate_context(agent_type):
                subscriptions_list_result = subscriptions()
                if inspect.isawaitable(subscriptions_list_result):
                    subscriptions_list.extend(await subscriptions_list_result)
                else:
                    # just ignore mypy here
                    subscriptions_list.extend(subscriptions_list_result)  # type: ignore

        agent_type = await runtime.register_factory(
            type=agent_type,
            agent_factory=lambda: ClosureAgent(description=description, closure=closure),
            expected_class=cls,
        )
        for subscription in subscriptions_list:
            await runtime.add_subscription(subscription)

        handled_types = get_handled_types_from_closure(closure)
        for message_type in handled_types:
            # TODO: support custom serializers
            serializer = try_get_known_serializers_for_type(message_type)
            runtime.add_message_serializer(serializer)

        return agent_type
