"""Input function type definitions for approval guard and user interactions."""

from typing import Awaitable, Callable, Optional, Union
from autogen_core import CancellationToken

# Type definitions for sync and async input functions
SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]