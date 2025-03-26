from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator

from autogen_core import AgentId, AgentRuntime, TopicId


class AgentChatRuntimeContext:
    """A static class that provides context for any agents running within a team.

    This static class can be used to access the current runtime and output topic
    during agent instantiation -- inside the factory function or the agent's
    class constructor.

    This allows agents to publish messages to the output topic which thereby allowing
    observability into any streaming components running within non-streaming contexts.
    """

    def __init__(self) -> None:
        raise RuntimeError(
            "AgentChatRuntimeContext cannot be instantiated. It is a static class that provides context management for an agent within a team."
        )

    _AGENT_RUNTIME_CONTEXT_VAR: ClassVar[ContextVar[tuple[AgentRuntime, TopicId]]] = ContextVar(
        "_AGENT_RUNTIME_CONTEXT_VAR"
    )

    @classmethod
    @contextmanager
    def populate_context(cls, ctx: tuple[AgentRuntime, TopicId]) -> Generator[None, Any, None]:
        """:meta private:"""
        token = AgentChatRuntimeContext._AGENT_RUNTIME_CONTEXT_VAR.set(ctx)
        try:
            yield
        finally:
            AgentChatRuntimeContext._AGENT_RUNTIME_CONTEXT_VAR.reset(token)

    @classmethod
    def current_runtime(cls) -> AgentRuntime:
        try:
            return cls._AGENT_RUNTIME_CONTEXT_VAR.get()[0]
        except LookupError as e:
            raise RuntimeError(
                "AgentChatRuntimeContext.current_runtime() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e

    @classmethod
    def output_channel(cls) -> TopicId:
        try:
            return cls._AGENT_RUNTIME_CONTEXT_VAR.get()[1]
        except LookupError as e:
            raise RuntimeError(
                "AgentChatRuntimeContext.output_channel() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e
