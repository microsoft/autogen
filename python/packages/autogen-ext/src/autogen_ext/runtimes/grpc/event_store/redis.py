import redis

class RedisEventStore():
    def __init__(self, redis_instance: redis.Redis, client_id):
        self.client_id = client_id
        self.store = redis_instance

    def push(self, message):
        self.store.rpush(self.client_id, message)
    
    def pop(self):
        return self.store.lpop(self.client_id)

