from __future__ import annotations

from asyncio import Future
from typing import Any, Callable, Mapping, Protocol, Sequence, Type, TypeVar, overload, runtime_checkable

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_proxy import AgentProxy
from ._cancellation_token import CancellationToken

# Undeliverable - error

T = TypeVar("T", bound=Agent)


class AllNamespaces:
    pass


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
        self, name: str, agent_factory: Callable[[], T], *, valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...
    ) -> None: ...

    @overload
    def register(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
        *,
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...,
    ) -> None: ...

    def register(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
        *,
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = AllNamespaces,
    ) -> None: ...

    def get(self, name: str, *, namespace: str = "default") -> AgentId: ...
    def get_proxy(self, name: str, *, namespace: str = "default") -> AgentProxy: ...

    @overload
    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T],
        *,
        namespace: str = "default",
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...,
    ) -> AgentId: ...

    @overload
    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...,
    ) -> AgentId: ...

    def register_and_get(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = AllNamespaces,
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
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...,
    ) -> AgentProxy: ...

    @overload
    def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = ...,
    ) -> AgentProxy: ...

    def register_and_get_proxy(
        self,
        name: str,
        agent_factory: Callable[[], T] | Callable[[AgentRuntime, AgentId], T],
        *,
        namespace: str = "default",
        valid_namespaces: Sequence[str] | Type[AllNamespaces] = AllNamespaces,
    ) -> AgentProxy:
        self.register(name, agent_factory)
        return self.get_proxy(name, namespace=namespace)

    def save_state(self) -> Mapping[str, Any]: ...

    def load_state(self, state: Mapping[str, Any]) -> None: ...

    def agent_metadata(self, agent: AgentId) -> AgentMetadata: ...

    def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]: ...

    def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None: ...
