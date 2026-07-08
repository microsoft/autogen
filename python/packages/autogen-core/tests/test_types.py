from dataclasses import dataclass
from types import NoneType
from typing import Any, List, Optional, Union

from autogen_core import MessageContext
from autogen_core._routed_agent import RoutedAgent, message_handler
from autogen_core._serialization import has_nested_base_model
from autogen_core._type_helpers import AnyType, get_types
from pydantic import BaseModel


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
    class HandlerClass(RoutedAgent):
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


class HandlerClass(RoutedAgent):
    @message_handler()
    async def handler(self, message: int, ctx: MessageContext) -> Any:
        return None


def test_nested_data_model() -> None:
    class MyBaseModel(BaseModel):
        message: str

    @dataclass
    class NestedBaseModel:
        nested: MyBaseModel

    @dataclass
    class NestedBaseModelList:
        nested: List[MyBaseModel]

    @dataclass
    class NestedBaseModelList2:
        nested: List[MyBaseModel]

    @dataclass
    class NestedBaseModelList3:
        nested: List[List[MyBaseModel]]

    @dataclass
    class NestedBaseModelList4:
        nested: List[List[List[List[List[List[MyBaseModel]]]]]]

    @dataclass
    class NestedBaseModelUnion:
        nested: Union[MyBaseModel, str]

    @dataclass
    class NestedBaseModelUnion2:
        nested: MyBaseModel | str

    assert has_nested_base_model(NestedBaseModel)
    assert has_nested_base_model(NestedBaseModelList)
    assert has_nested_base_model(NestedBaseModelList2)
    assert has_nested_base_model(NestedBaseModelList3)
    assert has_nested_base_model(NestedBaseModelList4)
    assert has_nested_base_model(NestedBaseModelUnion)
    assert has_nested_base_model(NestedBaseModelUnion2)
