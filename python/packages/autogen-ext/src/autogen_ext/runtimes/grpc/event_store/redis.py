import redis
from .store import EventStore

class RedisEventStore(EventStore):
    def __init__(self, redis_instance: redis.Redis, client_id):
        self.client_id = client_id
        self.store = redis_instance

    async def put(self, message):
        self.store.rpush(self.client_id, message)

    async def get(self):
        return self.store.blpop(self.client_id)

