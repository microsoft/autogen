from types import NoneType
from typing import Any, Optional, Union

from autogen_core.components._routed_agent import message_handler
from autogen_core.components._type_helpers import AnyType, get_types
from autogen_core.base import MessageContext


def test_get_types() -> None:
    assert get_types(Union[int, str]) == (int, str)
    assert get_types(int | str) == (int, str)
    assert get_types(int) == (int,)
    assert get_types(str) == (str,)
    assert get_types("test") is None
    assert get_types(Optional[int]) == (int, NoneType)
    assert get_types(NoneType) == (NoneType,)
    assert get_types(None) == (NoneType,)


def test_handler() -> None:

    class HandlerClass:
        @message_handler()
        async def handler(self, message: int, ctx: MessageContext) -> Any:
            return None

        @message_handler()
        async def handler2(self, message: str | bool, ctx: MessageContext) -> None:
            return None

    assert HandlerClass.handler.target_types == [int]
    assert HandlerClass.handler.produces_types == [AnyType]

    assert HandlerClass.handler2.target_types == [str, bool]
    assert HandlerClass.handler2.produces_types == [NoneType]

class HandlerClass:
    @message_handler()
    async def handler(self, message: int, ctx: MessageContext) -> Any:
        return None
