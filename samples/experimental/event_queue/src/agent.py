import asyncio
import datetime
from typing import List

from .events import AsyncEventQueue, Event, Message, NewMessageEvent, default_queue, on


class Agent:

    queue: AsyncEventQueue = default_queue

    def __init__(self, name: str) -> None:
        self.name = name
        # self._register_event_handlers()
        self._register_task = asyncio.create_task(self._register_event_handlers())

    async def _register_event_handlers(self) -> None:
        tasks: List[asyncio.Task[None]] = []
        for method_name in dir(self):
            method = getattr(self, method_name)
            if hasattr(method, "event_class"):
                task = asyncio.create_task(self.queue.subscribe(method.event_class, method))
                tasks.append(task)
        await asyncio.gather(*tasks)

    async def post_event(self, event: Event) -> None:
        if not self._register_task.done():
            await self._register_task
        await self.queue.post(event)
