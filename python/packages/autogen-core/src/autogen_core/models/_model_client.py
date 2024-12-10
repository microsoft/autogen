from __future__ import annotations

from typing import Mapping, Optional, Sequence, runtime_checkable

from typing_extensions import (
    Any,
    AsyncGenerator,
    Protocol,
    Required,
    TypedDict,
    Union,
)

from .. import CancellationToken
from ..tools import Tool, ToolSchema
from ._types import CreateResult, LLMMessage, RequestUsage


class ModelCapabilities(TypedDict, total=False):
    vision: Required[bool]
    function_calling: Required[bool]
    json_output: Required[bool]


@runtime_checkable
class ChatCompletionClient(Protocol):
    # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult: ...

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]: ...

    def actual_usage(self) -> RequestUsage: ...

    def total_usage(self) -> RequestUsage: ...

    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    @property
    def capabilities(self) -> ModelCapabilities: ...
