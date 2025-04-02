from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator

from ._agent_id import AgentId


class MessageHandlerContext:
    def __init__(self) -> None:
        raise RuntimeError(
            "MessageHandlerContext cannot be instantiated. It is a static class that provides context management for message handling."
        )

    _MESSAGE_HANDLER_CONTEXT: ClassVar[ContextVar[AgentId]] = ContextVar("_MESSAGE_HANDLER_CONTEXT")

    @classmethod
    @contextmanager
    def populate_context(cls, ctx: AgentId) -> Generator[None, Any, None]:
        """:meta private:"""
        token = MessageHandlerContext._MESSAGE_HANDLER_CONTEXT.set(ctx)
        try:
            yield
        finally:
            MessageHandlerContext._MESSAGE_HANDLER_CONTEXT.reset(token)

    @classmethod
    def agent_id(cls) -> AgentId:
        try:
            return cls._MESSAGE_HANDLER_CONTEXT.get()
        except LookupError as e:
            raise RuntimeError("MessageHandlerContext.agent_id() must be called within a message handler.") from e
