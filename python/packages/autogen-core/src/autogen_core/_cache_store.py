from abc import ABC, abstractmethod
from typing import Dict, Generic, Optional, TypeVar

from pydantic import BaseModel
from typing_extensions import Self

from ._component_config import Component, ComponentBase

T = TypeVar("T")


class CacheStore(ABC, Generic[T], ComponentBase[BaseModel]):
    """
    This protocol defines the basic interface for store/cache operations.

    Sub-classes should handle the lifecycle of underlying storage.
    """

    component_type = "cache_store"

    @abstractmethod
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Retrieve an item from the store.

        Args:
            key: The key identifying the item in the store.
            default (optional): The default value to return if the key is not found.
                                Defaults to None.

        Returns:
            The value associated with the key if found, else the default value.
        """
        ...

    @abstractmethod
    def set(self, key: str, value: T) -> None:
        """
        Set an item in the store.

        Args:
            key: The key under which the item is to be stored.
            value: The value to be stored in the store.
        """
        ...


class InMemoryStoreConfig(BaseModel):
    pass


class InMemoryStore(CacheStore[T], Component[InMemoryStoreConfig]):
    component_provider_override = "autogen_core.InMemoryStore"
    component_config_schema = InMemoryStoreConfig

    def __init__(self) -> None:
        self.store: Dict[str, T] = {}

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        return self.store.get(key, default)

    def set(self, key: str, value: T) -> None:
        self.store[key] = value

    def _to_config(self) -> InMemoryStoreConfig:
        return InMemoryStoreConfig()

    @classmethod
    def _from_config(cls, config: InMemoryStoreConfig) -> Self:
        return cls()
