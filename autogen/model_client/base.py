from __future__ import annotations


from typing_extensions import Self, Union, List, Any, Dict, Protocol, AsyncGenerator
from autogen.cache.cache import Cache
from .types import ChatMessage, CreateResponse, ToolCall


class TextModelClient(Protocol):

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> TextModelClient:
        raise NotImplementedError

    # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
    async def create(self, messages: List[ChatMessage], cache: Cache, extra_create_args: Dict[str, Any]) -> CreateResponse:
        raise NotImplementedError

    def create_stream(self, messages: List[ChatMessage], cache: Cache, extra_create_args: Dict[str, Any]) -> AsyncGenerator[Union[Union[str, ToolCall, CreateResponse]], None]:
        raise NotImplementedError






