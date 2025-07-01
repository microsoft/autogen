from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Tuple

from ._backend import _BACKENDS, get_backend


def compile(
    agent: Any,
    trainset: Iterable[Any],
    metric: Callable[[Any, Any], float | bool],
    *,
    backend: str = "dspy",
    **kwargs: Any,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Optimise the `system_message` and tool descriptions of an AutoGen agent.

    Parameters
    ----------
    agent
        Any subclass of autogen_core.agents.base.Agent.
    trainset
        Iterable of supervision examples (DSPy Examples or anything the
        back-end accepts).
    metric
        Callable(gold, pred) → float | bool used by the optimiser.
    backend
        Name of the registered optimisation backend (default: "dspy").
    kwargs
        Extra parameters forwarded verbatim to the backend.

    Returns
    -------
    (optimised_agent, report)
    """
    backend_impl = get_backend(backend)
    return backend_impl.compile(agent, trainset, metric, **kwargs)


def list_backends() -> List[str]:
    """Return the names of all available optimisation back-ends."""
    return sorted(_BACKENDS.keys())