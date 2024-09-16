import inspect
from typing import Any, Awaitable, Callable, Mapping, Sequence, TypeVar, get_type_hints

from autogen_core.base import MessageContext

from ..base._agent import Agent
from ..base._agent_id import AgentId
from ..base._agent_instantiation import AgentInstantiationContext
from ..base._agent_metadata import AgentMetadata
from ..base._agent_runtime import AgentRuntime
from ..base._serialization import JSON_DATA_CONTENT_TYPE, MESSAGE_TYPE_REGISTRY, try_get_known_serializers_for_type
from ..base._type_helpers import get_types
from ..base.exceptions import CantHandleException

T = TypeVar("T")


def get_subscriptions_from_closure(
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
        subscription_types = get_subscriptions_from_closure(closure)
        # TODO fold this into runtime
        for message_type in subscription_types:
            MESSAGE_TYPE_REGISTRY.add_serializer(try_get_known_serializers_for_type(message_type))

        self._subscriptions = [MESSAGE_TYPE_REGISTRY.type_name(message_type) for message_type in subscription_types]
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
        if MESSAGE_TYPE_REGISTRY.type_name(message) not in self._subscriptions:
            raise CantHandleException(
                f"Message type {type(message)} not in target types {self._subscriptions} of {self.id}"
            )
        return await self._closure(self._runtime, self._id, message, ctx)

    def save_state(self) -> Mapping[str, Any]:
        raise ValueError("save_state not implemented for ClosureAgent")

    def load_state(self, state: Mapping[str, Any]) -> None:
        raise ValueError("load_state not implemented for ClosureAgent")
