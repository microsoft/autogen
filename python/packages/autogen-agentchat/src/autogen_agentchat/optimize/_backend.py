from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, Tuple

# Simple registry so new back-ends can self-register
_BACKENDS: Dict[str, type["BaseBackend"]] = {}


class BaseBackend(ABC):
    """Contract every optimiser back-end must fulfil."""

    #: name used in compile(... backend="<name>")
    name: str = ""

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        if cls.name:
            _BACKENDS[cls.name] = cls

    # ---- required API --------------------------------------------------
    @abstractmethod
    def compile(
        self,
        agent: Any,
        trainset: Iterable[Any],
        metric: Callable[[Any, Any], float | bool],
        **kwargs: Any,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Return (optimised_agent, diagnostics/report)."""
        ...


def get_backend(name: str) -> BaseBackend:
    """Get a backend instance by name."""
    try:
        backend_cls = _BACKENDS[name]
        return backend_cls()
    except KeyError:
        raise ValueError(
            f"Unknown backend '{name}'. Available: {', '.join(_BACKENDS)}"
        ) from None