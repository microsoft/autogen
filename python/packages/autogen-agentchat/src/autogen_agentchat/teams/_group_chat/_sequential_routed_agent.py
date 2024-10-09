import asyncio
from typing import Any

from autogen_core.base import MessageContext
from autogen_core.components import RoutedAgent


class FIFOLock:
    """A lock that ensures coroutines acquire the lock in the order they request it."""

    def __init__(self) -> None:
        self._queue = asyncio.Queue[asyncio.Event]()
        self._locked = False

    async def acquire(self) -> None:
        # If the lock is not held by any coroutine, set the lock to be held
        # by the current coroutine.
        if not self._locked:
            self._locked = True
            return

        # If the lock is held by another coroutine, create an event and put it
        # in the queue. Wait for the event to be set.
        event = asyncio.Event()
        await self._queue.put(event)
        await event.wait()

    def release(self) -> None:
        if not self._queue.empty():
            # If there are events in the queue, get the next event and set it.
            next_event = self._queue.get_nowait()
            next_event.set()
        else:
            # If there are no events in the queue, release the lock.
            self._locked = False


class SequentialRoutedAgent(RoutedAgent):
    """A subclass of :class:`autogen_core.components.RoutedAgent` that ensures
    messages are handled sequentially in the order they arrive."""

    def __init__(self, description: str) -> None:
        super().__init__(description=description)
        self._fifo_lock = FIFOLock()

    async def on_message(self, message: Any, ctx: MessageContext) -> Any | None:
        await self._fifo_lock.acquire()
        try:
            return await super().on_message(message, ctx)
        finally:
            self._fifo_lock.release()
