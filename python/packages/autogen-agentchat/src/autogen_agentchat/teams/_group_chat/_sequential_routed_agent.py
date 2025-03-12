import asyncio
from typing import Any, Sequence

from autogen_core import MessageContext, RoutedAgent


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
    """A subclass of :class:`autogen_core.RoutedAgent` that ensures
    that messages of certain types are processed sequentially
    using a FIFO lock.

    This is useful for agents that need to maintain a strict order of
    processing messages, such as in a group chat scenario.



    Args:

        description (str): The description of the agent.
        sequential_message_types (Sequence[Type[Any]]): A sequence of message types that should be
            processed sequentially. If a message of one of these types is received,
            the agent will acquire a FIFO lock to ensure that it is processed
            before any later messages that are also one of these types.
    """

    def __init__(self, description: str, sequential_message_types: Sequence[type[Any]]) -> None:
        super().__init__(description=description)
        self._fifo_lock = FIFOLock()
        self._sequential_message_types = sequential_message_types

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any | None:
        if any(isinstance(message, sequential_type) for sequential_type in self._sequential_message_types):
            # Acquire the FIFO lock to ensure that this message is processed
            # in the order it was received.
            await self._fifo_lock.acquire()
            try:
                return await super().on_message_impl(message, ctx)
            finally:
                # Release the FIFO lock to allow the next message to be processed.
                self._fifo_lock.release()
        # If the message is not of a sequential type, process it normally.
        return await super().on_message_impl(message, ctx)
