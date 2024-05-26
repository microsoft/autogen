from typing import Any, Protocol, Sequence, runtime_checkable

from agnext.core.cancellation_token import CancellationToken


@runtime_checkable
class Agent(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def subscriptions(self) -> Sequence[type]: ...

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any | None: ...
