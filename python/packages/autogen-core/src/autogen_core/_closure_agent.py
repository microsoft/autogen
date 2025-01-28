from __future__ import annotations

import inspect
import warnings
from typing import Any, Awaitable, Callable, List, Literal, Mapping, Protocol, Sequence, TypeVar, get_type_hints

from ._agent_id import AgentId
from ._agent_instantiation import AgentInstantiationContext
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._agent_type import AgentType
from ._base_agent import BaseAgent
from ._cancellation_token import CancellationToken
from ._message_context import MessageContext
from ._serialization import try_get_known_serializers_for_type
from ._subscription import Subscription
from ._subscription_context import SubscriptionInstantiationContext
from ._topic import TopicId
from ._type_helpers import get_types
from .exceptions import CantHandleException

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
        message_id: str | None = None,
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
        self,
        description: str,
        closure: Callable[[ClosureContext, T, MessageContext], Awaitable[Any]],
        *,
        unknown_type_policy: Literal["error", "warn", "ignore"] = "warn",
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
        self._unknown_type_policy = unknown_type_policy
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
            if self._unknown_type_policy == "warn":
                warnings.warn(
                    f"Message type {type(message)} not in target types {self._expected_types} of {self.id}. Set unknown_type_policy to 'error' to raise an exception, or 'ignore' to suppress this warning.",
                    stacklevel=1,
                )
                return None
            elif self._unknown_type_policy == "error":
                raise CantHandleException(
                    f"Message type {type(message)} not in target types {self._expected_types} of {self.id}. Set unknown_type_policy to 'warn' to suppress this exception, or 'ignore' to suppress this warning."
                )

        return await self._closure(self, message, ctx)

    async def save_state(self) -> Mapping[str, Any]:
        """Closure agents do not have state. So this method always returns an empty dictionary."""
        return {}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Closure agents do not have state. So this method does nothing."""
        pass

    @classmethod
    async def register_closure(
        cls,
        runtime: AgentRuntime,
        type: str,
        closure: Callable[[ClosureContext, T, MessageContext], Awaitable[Any]],
        *,
        unknown_type_policy: Literal["error", "warn", "ignore"] = "warn",
        skip_direct_message_subscription: bool = False,
        description: str = "",
        subscriptions: Callable[[], list[Subscription] | Awaitable[list[Subscription]]] | None = None,
    ) -> AgentType:
        """The closure agent allows you to define an agent using a closure, or function without needing to define a class. It allows values to be extracted out of the runtime.

        The closure can define the type of message which is expected, or `Any` can be used to accept any type of message.

        Example:

        .. code-block:: python

            import asyncio
            from autogen_core import SingleThreadedAgentRuntime, MessageContext, ClosureAgent, ClosureContext
            from dataclasses import dataclass

            from autogen_core._default_subscription import DefaultSubscription
            from autogen_core._default_topic import DefaultTopicId


            @dataclass
            class MyMessage:
                content: str


            async def main():
                queue = asyncio.Queue[MyMessage]()

                async def output_result(_ctx: ClosureContext, message: MyMessage, ctx: MessageContext) -> None:
                    await queue.put(message)

                runtime = SingleThreadedAgentRuntime()
                await ClosureAgent.register_closure(
                    runtime, "output_result", output_result, subscriptions=lambda: [DefaultSubscription()]
                )

                runtime.start()
                await runtime.publish_message(MyMessage("Hello, world!"), DefaultTopicId())
                await runtime.stop_when_idle()

                result = await queue.get()
                print(result)


            asyncio.run(main())


        Args:
            runtime (AgentRuntime): Runtime to register the agent to
            type (str): Agent type of registered agent
            closure (Callable[[ClosureContext, T, MessageContext], Awaitable[Any]]): Closure to handle messages
            unknown_type_policy (Literal["error", "warn", "ignore"], optional): What to do if a type is encountered that does not match the closure type. Defaults to "warn".
            skip_direct_message_subscription (bool, optional): Do not add direct message subscription for this agent. Defaults to False.
            description (str, optional): Description of what agent does. Defaults to "".
            subscriptions (Callable[[], list[Subscription]  |  Awaitable[list[Subscription]]] | None, optional): List of subscriptions for this closure agent. Defaults to None.

        Returns:
            AgentType: Type of the agent that was registered
        """

        def factory() -> ClosureAgent:
            return ClosureAgent(description=description, closure=closure, unknown_type_policy=unknown_type_policy)

        assert len(cls._unbound_subscriptions()) == 0, "Closure agents are expected to have no class subscriptions"
        agent_type = await cls.register(
            runtime=runtime,
            type=type,
            factory=factory,  # type: ignore
            # There should be no need to process class subscriptions, as the closure agent does not have any subscriptions.s
            skip_class_subscriptions=True,
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
