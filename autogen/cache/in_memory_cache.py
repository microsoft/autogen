import sys
from types import TracebackType
from typing import Any, Dict, Optional, Type, Union

from .abstract_cache_base import AbstractCache

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class InMemoryCache(AbstractCache):

    def __init__(self, seed: Union[str, int] = ""):
        self._seed = str(seed)
        self._cache: Dict[str, Any] = {}

    def _prefixed_key(self, key: str) -> str:
        separator = "_" if self._seed else ""
        return f"{self._seed}{separator}{key}"

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        result = self._cache.get(self._prefixed_key(key))
        if result is None:
            return default
        return result

    def set(self, key: str, value: Any) -> None:
        self._cache[self._prefixed_key(key)] = value

    def close(self) -> None:
        pass

    def __enter__(self) -> Self:
        """
        Enter the runtime context related to the object.

        Returns:
            self: The instance itself.
        """
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        """
        Exit the runtime context related to the object.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_value: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.
        """
        self.close()
