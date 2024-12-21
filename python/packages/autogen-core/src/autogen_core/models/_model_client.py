from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping, Optional, Sequence

from typing_extensions import (
    Any,
    AsyncGenerator,
    Required,
    TypedDict,
    Union,
)

from .. import CancellationToken
from .._component_config import ComponentLoader
from ..tools import Tool, ToolSchema
from ._types import CreateResult, LLMMessage, RequestUsage


class ModelCapabilities(TypedDict, total=False):
    vision: Required[bool]
    function_calling: Required[bool]
    json_output: Required[bool]


class ChatCompletionClient(ABC, ComponentLoader):
    # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def actual_usage(self) -> RequestUsage: ...

    @abstractmethod
    def total_usage(self) -> RequestUsage: ...

    @abstractmethod
    def count_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    @abstractmethod
    def remaining_tokens(self, messages: Sequence[LLMMessage], tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities: ...
