from __future__ import annotations


from typing import Optional
from typing_extensions import Union, List, Any, Dict, Protocol, AsyncGenerator
from autogen.cache.cache import AbstractCache
from .types import ChatMessage, CreateResponse, RequestUsage, ToolCall

class ChatModelClient(Protocol):
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatModelClient:
        ...

    # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
    async def create(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> CreateResponse:
        ...

    def create_stream(
        self, messages: List[ChatMessage], cache: Optional[AbstractCache] = None, extra_create_args: Dict[str, Any] = {}
    ) -> AsyncGenerator[Union[Union[str, ToolCall, CreateResponse]], None]:
        ...

    def actual_usage(self) -> RequestUsage:
        ...

    def total_usage(self) -> RequestUsage:
        ...
