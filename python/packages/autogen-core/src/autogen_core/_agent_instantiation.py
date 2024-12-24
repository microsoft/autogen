from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator

from ._agent_id import AgentId
from ._agent_runtime import AgentRuntime


class AgentInstantiationContext:
    def __init__(self) -> None:
        raise RuntimeError(
            "AgentInstantiationContext cannot be instantiated. It is a static class that provides context management for agent instantiation."
        )

    _AGENT_INSTANTIATION_CONTEXT_VAR: ClassVar[ContextVar[tuple[AgentRuntime, AgentId]]] = ContextVar(
        "_AGENT_INSTANTIATION_CONTEXT_VAR"
    )

    @classmethod
    @contextmanager
    def populate_context(cls, ctx: tuple[AgentRuntime, AgentId]) -> Generator[None, Any, None]:
        """:meta private:"""
        token = AgentInstantiationContext._AGENT_INSTANTIATION_CONTEXT_VAR.set(ctx)
        try:
            yield
        finally:
            AgentInstantiationContext._AGENT_INSTANTIATION_CONTEXT_VAR.reset(token)

    @classmethod
    def current_runtime(cls) -> AgentRuntime:
        try:
            return cls._AGENT_INSTANTIATION_CONTEXT_VAR.get()[0]
        except LookupError as e:
            raise RuntimeError(
                "AgentInstantiationContext.runtime() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e

    @classmethod
    def current_agent_id(cls) -> AgentId:
        try:
            return cls._AGENT_INSTANTIATION_CONTEXT_VAR.get()[1]
        except LookupError as e:
            raise RuntimeError(
                "AgentInstantiationContext.agent_id() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e
