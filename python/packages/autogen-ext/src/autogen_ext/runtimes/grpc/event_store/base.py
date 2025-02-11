
class EventStore():
    async def put(self, message):
        raise NotImplementedError
    async def get(self):
        raise NotImplementedError
