from typing import Any

try:
    from termcolor import colored
except ImportError:  # pragma: no cover

    def colored(text: Any, *args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
        return str(text)


__all__ = ("colored",)
