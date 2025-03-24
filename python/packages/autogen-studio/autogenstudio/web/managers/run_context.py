from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator


class RunContext:
    RUN_CONTEXT_VAR: ClassVar[ContextVar] = ContextVar("RUN_CONTEXT_VAR")

    @classmethod
    @contextmanager
    def populate_context(cls, run_id) -> Generator[None, Any, None]:
        token = RunContext.RUN_CONTEXT_VAR.set(run_id)
        try:
            yield
        finally:
            RunContext.RUN_CONTEXT_VAR.reset(token)

    @classmethod
    def current_run_id(cls) -> str:
        try:
            return cls.RUN_CONTEXT_VAR.get()
        except LookupError as e:
            raise RuntimeError("Error getting run id") from e
