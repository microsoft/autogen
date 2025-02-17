from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Awaitable, Callable, Mapping, Protocol, Type, TypeVar, overload, runtime_checkable

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_type import AgentType
from ._cancellation_token import CancellationToken
from ._serialization import MessageSerializer
from ._subscription import Subscription
from ._topic import TopicId

# Undeliverable - error

T = TypeVar("T", bound=Agent)


@runtime_checkable
class AgentRuntime(Protocol):
    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> Any:
        """Send a message to an agent and get a response.

        Args:
            message (Any): The message to send.
            recipient (AgentId): The agent to send the message to.
            sender (AgentId | None, optional): Agent which sent the message. Should **only** be None if this was sent from no agent, such as directly to the runtime externally. Defaults to None.
            cancellation_token (CancellationToken | None, optional): Token used to cancel an in progress . Defaults to None.

        Raises:
            CantHandleException: If the recipient cannot handle the message.
            UndeliverableException: If the message cannot be delivered.
            Other: Any other exception raised by the recipient.

        Returns:
            Any: The response from the agent.
        """

        ...

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        """Publish a message to all agents in the given namespace, or if no namespace is provided, the namespace of the sender.

        No responses are expected from publishing.

        Args:
            message (Any): The message to publish.
            topic (TopicId): The topic to publish the message to.
            sender (AgentId | None, optional): The agent which sent the message. Defaults to None.
            cancellation_token (CancellationToken | None, optional): Token used to cancel an in progress. Defaults to None.
            message_id (str | None, optional): The message id. If None, a new message id will be generated. Defaults to None. This message id must be unique. and is recommended to be a UUID.

        Raises:
            UndeliverableException: If the message cannot be delivered.
        """
        ...

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None,
    ) -> AgentType:
        """Register an agent factory with the runtime associated with a specific type. The type must be unique. This API does not add any subscriptions.

        .. note::

            This is a low level API and usually the agent class's `register` method should be used instead, as this also handles subscriptions automatically.

        Example:

        .. code-block:: python

            from dataclasses import dataclass

            from autogen_core import AgentRuntime, MessageContext, RoutedAgent, event
            from autogen_core.models import UserMessage


            @dataclass
            class MyMessage:
                content: str


            class MyAgent(RoutedAgent):
                def __init__(self) -> None:
                    super().__init__("My core agent")

                @event
                async def handler(self, message: UserMessage, context: MessageContext) -> None:
                    print("Event received: ", message.content)


            async def my_agent_factory():
                return MyAgent()


            async def main() -> None:
                runtime: AgentRuntime = ...  # type: ignore
                await runtime.register_factory("my_agent", lambda: MyAgent())


            import asyncio

            asyncio.run(main())


        Args:
            type (str): The type of agent this factory creates. It is not the same as agent class name. The `type` parameter is used to differentiate between different factory functions rather than agent classes.
            agent_factory (Callable[[], T]): The factory that creates the agent, where T is a concrete Agent type. Inside the factory, use `autogen_core.AgentInstantiationContext` to access variables like the current runtime and agent ID.
            expected_class (type[T] | None, optional): The expected class of the agent, used for runtime validation of the factory. Defaults to None. If None, no validation is performed.
        """
        ...

    # TODO: uncomment out the following type ignore when this is fixed in mypy: https://github.com/python/mypy/issues/3737
    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        """Try to get the underlying agent instance by name and namespace. This is generally discouraged (hence the long name), but can be useful in some cases.

        If the underlying agent is not accessible, this will raise an exception.

        Args:
            id (AgentId): The agent id.
            type (Type[T], optional): The expected type of the agent. Defaults to Agent.

        Returns:
            T: The concrete agent instance.

        Raises:
            LookupError: If the agent is not found.
            NotAccessibleError: If the agent is not accessible, for example if it is located remotely.
            TypeError: If the agent is not of the expected type.
        """
        ...

    @overload
    async def get(self, id: AgentId, /, *, lazy: bool = ...) -> AgentId: ...

    @overload
    async def get(self, type: AgentType | str, /, key: str = ..., *, lazy: bool = ...) -> AgentId: ...

    async def get(
        self, id_or_type: AgentId | AgentType | str, /, key: str = "default", *, lazy: bool = True
    ) -> AgentId: ...

    async def save_state(self) -> Mapping[str, Any]:
        """Save the state of the entire runtime, including all hosted agents. The only way to restore the state is to pass it to :meth:`load_state`.

        The structure of the state is implementation defined and can be any JSON serializable object.

        Returns:
            Mapping[str, Any]: The saved state.
        """
        ...

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the state of the entire runtime, including all hosted agents. The state should be the same as the one returned by :meth:`save_state`.

        Args:
            state (Mapping[str, Any]): The saved state.
        """
        ...

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        """Get the metadata for an agent.

        Args:
            agent (AgentId): The agent id.

        Returns:
            AgentMetadata: The agent metadata.
        """
        ...

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        """Save the state of a single agent.

        The structure of the state is implementation defined and can be any JSON serializable object.

        Args:
            agent (AgentId): The agent id.

        Returns:
            Mapping[str, Any]: The saved state.
        """
        ...

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        """Load the state of a single agent.

        Args:
            agent (AgentId): The agent id.
            state (Mapping[str, Any]): The saved state.
        """
        ...

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription that the runtime should fulfill when processing published messages

        Args:
            subscription (Subscription): The subscription to add
        """
        ...

    async def remove_subscription(self, id: str) -> None:
        """Remove a subscription from the runtime

        Args:
            id (str): id of the subscription to remove

        Raises:
            LookupError: If the subscription does not exist
        """
        ...

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        """Add a new message serialization serializer to the runtime

        Note: This will deduplicate serializers based on the type_name and data_content_type properties

        Args:
            serializer (MessageSerializer[Any] | Sequence[MessageSerializer[Any]]): The serializer/s to add
        """
        ...
