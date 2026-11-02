import threading
from asyncio import Future, get_running_loop
from typing import Any, Callable, List


class CancellationToken:
    """A token used to cancel pending async calls"""

    def __init__(self) -> None:
        self._cancelled: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._callbacks: List[Callable[[], None]] = []

    def cancel(self) -> None:
        """Cancel pending async calls linked to this cancellation token."""
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                for callback in self._callbacks:
                    callback()

    def is_cancelled(self) -> bool:
        """Check if the CancellationToken has been used"""
        with self._lock:
            return self._cancelled

    def add_callback(self, callback: Callable[[], None]) -> None:
        """Attach a callback that will be called when cancel is invoked"""
        with self._lock:
            if self._cancelled:
                callback()
            else:
                self._callbacks.append(callback)

    @staticmethod
    def _cancel_future(future: Future[Any]) -> None:
        if future.done():
            return

        loop = future.get_loop()
        try:
            same_loop = get_running_loop() is loop
        except RuntimeError:
            same_loop = False

        if loop.is_running() and not same_loop:
            loop.call_soon_threadsafe(future.cancel)
        else:
            future.cancel()

    def link_future(self, future: Future[Any]) -> Future[Any]:
        """Link a pending async call to a token to allow its cancellation"""
        with self._lock:
            if self._cancelled:
                self._cancel_future(future)
            else:
                self._callbacks.append(lambda: self._cancel_future(future))
        return future
