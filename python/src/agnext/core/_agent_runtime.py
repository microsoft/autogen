from __future__ import annotations

from asyncio import Future
from contextvars import ContextVar
from typing import Any, Callable, Mapping, Protocol, TypeVar, overload, runtime_checkable

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_proxy import AgentProxy
from ._cancellation_token import CancellationToken

# Undeliverable - error

T = TypeVar("T", bound=Agent)

agent_instantiation_context: ContextVar[tuple[AgentRuntime, AgentId]] = ContextVar("agent_instantiation_context")


@runtime_checkable
class AgentRuntime(Protocol):
    # Returns the response of the message
    def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]: ...

    # No responses from publishing
    def publish_message(
        self,
        message: Any,
        *,
        namespace: str | None = None,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]: ...

    @overload
    def register(
        self,
        name: str,
        agent_factory: Callable[[], T],
    ) -> None: ...

    @overload
    def register(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
    ) -> None: ...

    def register(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
    ) -> None:
        """Register an agent factory with the runtime associated with a specific name. The name must be unique.

        Args:
            name (str): The name of the type agent this factory creates.
            agent_factory (Callable[[], T] | Callable[[AgentRuntime, AgentId], T]): The factory that creates the agent.


        Example:
            .. code-block:: python

                runtime.register(
                    "chat_agent",
                    lambda: ChatCompletionAgent(
                        description="A generic chat agent.",
                        system_messages=[SystemMessage("You are a helpful assistant")],
                        model_client=OpenAI(model="gpt-4o"),
                        memory=BufferedChatMemory(buffer_size=10),
                    ),
                )

        """

        ...

    def get(self, name: str, *, namespace: str = "default") -> AgentId: ...
    def get_proxy(self, name: str, *, namespace: str = "default") -> AgentProxy: ...

    @overload
    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T],
        *,
        namespace: str = "default",
    ) -> AgentId: ...

    @overload
    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
    ) -> AgentId: ...

    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
    ) -> AgentId:
        self.register(name, agent_factory)
        return self.get(name, namespace=namespace)

    @overload
    def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[], T],
        *,
        namespace: str = "default",
    ) -> AgentProxy: ...

    @overload
    def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
    ) -> AgentProxy: ...

    def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
    ) -> AgentProxy:
        self.register(name, agent_factory)
        return self.get_proxy(name, namespace=namespace)

    def save_state(self) -> Mapping[str, Any]: ...

    def load_state(self, state: Mapping[str, Any]) -> None: ...

    def agent_metadata(self, agent: AgentId) -> AgentMetadata: ...

    def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]: ...

    def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None: ...
