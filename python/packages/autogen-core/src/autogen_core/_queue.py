# Copy of Asyncio queue: https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py
# So that shutdown can be used in <3.13
# Modified to work outside of the asyncio package

import asyncio
import collections
import threading
from typing import Generic, TypeVar

_global_lock = threading.Lock()


class _LoopBoundMixin:
    _loop = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.get_running_loop()

        if self._loop is None:
            with _global_lock:
                if self._loop is None:
                    self._loop = loop
        if loop is not self._loop:
            raise RuntimeError(f"{self!r} is bound to a different event loop")
        return loop


class QueueShutDown(Exception):
    """Raised when putting on to or getting from a shut-down Queue."""

    pass


T = TypeVar("T")


class Queue(_LoopBoundMixin, Generic[T]):
    def __init__(self, maxsize: int = 0):
        self._maxsize = maxsize
        self._getters = collections.deque[asyncio.Future[None]]()
        self._putters = collections.deque[asyncio.Future[None]]()
        self._unfinished_tasks = 0
        self._finished = asyncio.Event()
        self._finished.set()
        self._queue = collections.deque[T]()
        self._is_shutdown = False

    # These three are overridable in subclasses.

    def _get(self) -> T:
        return self._queue.popleft()

    def _put(self, item: T) -> None:
        self._queue.append(item)

    # End of the overridable methods.

    def _wakeup_next(self, waiters: collections.deque[asyncio.Future[None]]) -> None:
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self) -> str:
        return f"<{type(self).__name__} at {id(self):#x} {self._format()}>"

    def __str__(self) -> str:
        return f"<{type(self).__name__} {self._format()}>"

    def _format(self) -> str:
        result = f"maxsize={self._maxsize!r}"
        if getattr(self, "_queue", None):
            result += f" _queue={list(self._queue)!r}"
        if self._getters:
            result += f" _getters[{len(self._getters)}]"
        if self._putters:
            result += f" _putters[{len(self._putters)}]"
        if self._unfinished_tasks:
            result += f" tasks={self._unfinished_tasks}"
        if self._is_shutdown:
            result += " shutdown"
        return result

    def qsize(self) -> int:
        """Number of items in the queue."""
        return len(self._queue)

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return not self._queue

    def full(self) -> bool:
        """Return True if there are maxsize items in the queue.

        Note: if the Queue was initialized with maxsize=0 (the default),
        then full() is never True.
        """
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

    async def put(self, item: T) -> None:
        """Put an item into the queue.

        Put an item into the queue. If the queue is full, wait until a free
        slot is available before adding item.

        Raises QueueShutDown if the queue has been shut down.
        """
        while self.full():
            if self._is_shutdown:
                raise QueueShutDown
            putter = self._get_loop().create_future()
            self._putters.append(putter)
            try:
                await putter
            except:
                putter.cancel()  # Just in case putter is not done yet.
                try:
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
                except ValueError:
                    # The putter could be removed from self._putters by a
                    # previous get_nowait call or a shutdown call.
                    pass
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(item)

    def put_nowait(self, item: T) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.

        Raises QueueShutDown if the queue has been shut down.
        """
        if self._is_shutdown:
            raise QueueShutDown
        if self.full():
            raise asyncio.QueueFull
        self._put(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self) -> T:
        """Remove and return an item from the queue.

        If queue is empty, wait until an item is available.

        Raises QueueShutDown if the queue has been shut down and is empty, or
        if the queue has been shut down immediately.
        """
        while self.empty():
            if self._is_shutdown and self.empty():
                raise QueueShutDown
            getter = self._get_loop().create_future()
            self._getters.append(getter)
            try:
                await getter
            except:
                getter.cancel()  # Just in case getter is not done yet.
                try:
                    # Clean self._getters from canceled getters.
                    self._getters.remove(getter)
                except ValueError:
                    # The getter could be removed from self._getters by a
                    # previous put_nowait call, or a shutdown call.
                    pass
                if not self.empty() and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        return self.get_nowait()

    def get_nowait(self) -> T:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.

        Raises QueueShutDown if the queue has been shut down and is empty, or
        if the queue has been shut down immediately.
        """
        if self.empty():
            if self._is_shutdown:
                raise QueueShutDown
            raise asyncio.QueueEmpty
        item = self._get()
        self._wakeup_next(self._putters)
        return item

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete.

        Used by queue consumers. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items have
        been processed (meaning that a task_done() call was received for every
        item that had been put() into the queue).

        shutdown(immediate=True) calls task_done() for each remaining item in
        the queue.

        Raises ValueError if called more times than there were items placed in
        the queue.
        """
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self) -> None:
        """Block until all items in the queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer calls task_done() to
        indicate that the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        if self._unfinished_tasks > 0:
            await self._finished.wait()

    def shutdown(self, immediate: bool = False) -> None:
        """Shut-down the queue, making queue gets and puts raise QueueShutDown.

        By default, gets will only raise once the queue is empty. Set
        'immediate' to True to make gets raise immediately instead.

        All blocked callers of put() and get() will be unblocked. If
        'immediate', a task is marked as done for each item remaining in
        the queue, which may unblock callers of join().
        """
        self._is_shutdown = True
        if immediate:
            while not self.empty():
                self._get()
                if self._unfinished_tasks > 0:
                    self._unfinished_tasks -= 1
            if self._unfinished_tasks == 0:
                self._finished.set()
        # All getters need to re-check queue-empty to raise ShutDown
        while self._getters:
            getter = self._getters.popleft()
            if not getter.done():
                getter.set_result(None)
        while self._putters:
            putter = self._putters.popleft()
            if not putter.done():
                putter.set_result(None)
