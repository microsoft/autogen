from typing import Any, Dict, Optional, TypeVar, cast

import redis
from autogen_core import CacheStore, Component
from pydantic import BaseModel
from typing_extensions import Self

T = TypeVar("T")


class RedisStoreConfig(BaseModel):
    """Configuration for RedisStore"""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    # Add other relevant redis connection parameters
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: Optional[float] = None


class RedisStore(CacheStore[T], Component[RedisStoreConfig]):
    """
    A typed CacheStore implementation that uses redis as the underlying storage.
    See :class:`~autogen_ext.models.cache.ChatCompletionCache` for an example of usage.

    Args:
        cache_instance: An instance of `redis.Redis`.
                        The user is responsible for managing the Redis instance's lifetime.
    """

    component_config_schema = RedisStoreConfig
    component_provider_override = "autogen_ext.cache_store.redis.RedisStore"

    def __init__(self, redis_instance: redis.Redis):
        self.cache = redis_instance

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        value = cast(Optional[T], self.cache.get(key))
        if value is None:
            return default
        return value

    def set(self, key: str, value: T) -> None:
        self.cache.set(key, cast(Any, value))

    def _to_config(self) -> RedisStoreConfig:
        # Extract connection info from redis instance
        connection_pool = self.cache.connection_pool
        connection_kwargs: Dict[str, Any] = connection_pool.connection_kwargs  # type: ignore[reportUnknownMemberType]

        username = connection_kwargs.get("username")
        password = connection_kwargs.get("password")
        socket_timeout = connection_kwargs.get("socket_timeout")

        return RedisStoreConfig(
            host=str(connection_kwargs.get("host", "localhost")),
            port=int(connection_kwargs.get("port", 6379)),
            db=int(connection_kwargs.get("db", 0)),
            username=str(username) if username is not None else None,
            password=str(password) if password is not None else None,
            ssl=bool(connection_kwargs.get("ssl", False)),
            socket_timeout=float(socket_timeout) if socket_timeout is not None else None,
        )

    @classmethod
    def _from_config(cls, config: RedisStoreConfig) -> Self:
        # Create new redis instance from config
        redis_instance = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            username=config.username,
            password=config.password,
            ssl=config.ssl,
            socket_timeout=config.socket_timeout,
        )
        return cls(redis_instance=redis_instance)
