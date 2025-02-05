import asyncio
from .store import EventStore

class MemoryEventStore(EventStore):
    def __init__(self, client_id, **kwags):
        self.client_id = client_id
        self.store = asyncio.Queue()

    async def put(self, message):
        await self.store.put(self.client_id, message)

    async def get(self):
        return await self.store.get(self.client_id)
