import inspect
import threading
from asyncio import Future
from typing import Any, Awaitable, Callable, List


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._callbacks: List[Callable[[], None] | Callable[[], Awaitable[None]]] = []

    async def cancel(self) -> None:
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                for callback in self._callbacks:
                    res = callback()
                    if inspect.isawaitable(res):
                        await res

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def add_callback(self, callback: Callable[[], None] | Callable[[], Awaitable[None]]) -> None:
        with self._lock:
            if self._cancelled:
                callback()
            else:
                self._callbacks.append(callback)

    def link_future(self, future: Future[Any]) -> Future[Any]:
        with self._lock:
            if self._cancelled:
                future.cancel()
            else:

                def _cancel() -> None:
                    future.cancel()

                self._callbacks.append(_cancel)
        return future
