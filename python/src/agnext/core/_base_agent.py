import warnings
from abc import ABC, abstractmethod
from asyncio import Future
from typing import Any, Mapping, Sequence

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._cancellation_token import CancellationToken


class BaseAgent(ABC, Agent):
    @property
    def metadata(self) -> AgentMetadata:
        assert self._id is not None
        return AgentMetadata(
            namespace=self._id.namespace,
            name=self._id.name,
            description=self._description,
            subscriptions=self._subscriptions,
        )

    def __init__(self, description: str, subscriptions: Sequence[type]) -> None:
        self._runtime: AgentRuntime | None = None
        self._id: AgentId | None = None
        self._description = description
        self._subscriptions = subscriptions

    def bind_runtime(self, runtime: AgentRuntime) -> None:
        if self._runtime is not None:
            raise RuntimeError("Agent has already been bound to a runtime.")

        self._runtime = runtime

    def bind_id(self, agent_id: AgentId) -> None:
        if self._id is not None:
            raise RuntimeError("Agent has already been bound to an id.")
        self._id = agent_id

    @property
    def name(self) -> str:
        return self.id.name

    @property
    def id(self) -> AgentId:
        if self._id is None:
            raise RuntimeError("Agent has not been bound to an id.")

        return self._id

    @property
    def runtime(self) -> AgentRuntime:
        if self._runtime is None:
            raise RuntimeError("Agent has not been bound to a runtime.")

        return self._runtime

    @abstractmethod
    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any: ...

    # Returns the response of the message
    def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]:
        if self._runtime is None:
            raise RuntimeError("Agent has not been bound to a runtime.")

        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = self._runtime.send_message(
            message,
            sender=self.id,
            recipient=recipient,
            cancellation_token=cancellation_token,
        )
        cancellation_token.link_future(future)
        return future

    def publish_message(
        self,
        message: Any,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]:
        if self._runtime is None:
            raise RuntimeError("Agent has not been bound to a runtime.")

        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = self._runtime.publish_message(message, sender=self.id, cancellation_token=cancellation_token)
        return future

    def save_state(self) -> Mapping[str, Any]:
        warnings.warn("save_state not implemented", stacklevel=2)
        return {}

    def load_state(self, state: Mapping[str, Any]) -> None:
        warnings.warn("load_state not implemented", stacklevel=2)
        pass
