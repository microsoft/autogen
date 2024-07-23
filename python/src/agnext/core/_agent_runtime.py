from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Generator, Mapping, Protocol, Type, TypeVar, overload, runtime_checkable

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_proxy import AgentProxy
from ._cancellation_token import CancellationToken

# Undeliverable - error

T = TypeVar("T", bound=Agent)

AGENT_INSTANTIATION_CONTEXT_VAR: ContextVar[tuple[AgentRuntime, AgentId]] = ContextVar(
    "AGENT_INSTANTIATION_CONTEXT_VAR"
)


@contextmanager
def agent_instantiation_context(ctx: tuple[AgentRuntime, AgentId]) -> Generator[None, Any, None]:
    token = AGENT_INSTANTIATION_CONTEXT_VAR.set(ctx)
    try:
        yield
    finally:
        AGENT_INSTANTIATION_CONTEXT_VAR.reset(token)


@runtime_checkable
class AgentRuntime(Protocol):
    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
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
        *,
        namespace: str | None = None,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Publish a message to all agents in the given namespace, or if no namespace is provided, the namespace of the sender.

        No responses are expected from publishing.

        Args:
            message (Any): The message to publish.
            namespace (str | None, optional): The namespace to publish to. Defaults to None.
            sender (AgentId | None, optional): The agent which sent the message. Defaults to None.
            cancellation_token (CancellationToken | None, optional): Token used to cancel an in progress . Defaults to None.

        Raises:
            UndeliverableException: If the message cannot be delivered.
        """

    @overload
    async def register(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]],
    ) -> None: ...

    @overload
    async def register(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
    ) -> None: ...

    async def register(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
    ) -> None:
        """Register an agent factory with the runtime associated with a specific name. The name must be unique.

        Args:
            name (str): The name of the type agent this factory creates.
            agent_factory (Callable[[], T] | Callable[[AgentRuntime, AgentId], T]): The factory that creates the agent, where T is a concrete Agent type.


        Example:
            .. code-block:: python

                runtime.register(
                    "chat_agent",
                    lambda: ChatCompletionAgent(
                        description="A generic chat agent.",
                        system_messages=[SystemMessage("You are a helpful assistant")],
                        model_client=OpenAIChatCompletionClient(model="gpt-4o"),
                        memory=BufferedChatMemory(buffer_size=10),
                    ),
                )

        """

        ...

    async def get(self, name: str, *, namespace: str = "default") -> AgentId:
        """Get an agent by name and namespace.

        Args:
            name (str): The name of the agent.
            namespace (str, optional): The namespace of the agent. Defaults to "default".

        Returns:
            AgentId: The agent id.
        """
        ...

    async def get_proxy(self, name: str, *, namespace: str = "default") -> AgentProxy:
        """Get a proxy for an agent by name and namespace.

        Args:
            name (str): The name of the agent.
            namespace (str, optional): The namespace of the agent. Defaults to "default".

        Returns:
            AgentProxy: The agent proxy.
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
    async def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentId: ...

    @overload
    async def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentId: ...

    async def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentId:
        """Register an agent factory with the runtime associated with a specific name and get the agent id. The name must be unique.

        Args:
            name (str): The name of the type agent this factory creates.
            agent_factory (Callable[[], T] | Callable[[AgentRuntime, AgentId], T]): The factory that creates the agent, where T is a concrete Agent type.
            namespace (str, optional): The namespace of the agent. Defaults to "default".

        Returns:
            AgentId: The agent id.
        """
        await self.register(name, agent_factory)
        return await self.get(name, namespace=namespace)

    @overload
    async def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentProxy: ...

    @overload
    async def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentProxy: ...

    async def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        *,
        namespace: str = "default",
    ) -> AgentProxy:
        """Register an agent factory with the runtime associated with a specific name and get the agent proxy. The name must be unique.

        Args:
            name (str): The name of the type agent this factory creates.
            agent_factory (Callable[[], T] | Callable[[AgentRuntime, AgentId], T]): The factory that creates the agent, where T is a concrete Agent type.
            namespace (str, optional): The namespace of the agent. Defaults to "default".

        Returns:
            AgentProxy: The agent proxy.
        """
        await self.register(name, agent_factory)
        return await self.get_proxy(name, namespace=namespace)

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
