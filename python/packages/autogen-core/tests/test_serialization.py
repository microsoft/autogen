from dataclasses import dataclass

import pytest
from autogen_core.base import (
    JSON_DATA_CONTENT_TYPE,
    MessageSerializer,
    Serialization,
    try_get_known_serializers_for_type,
)
from pydantic import BaseModel


class PydanticMessage(BaseModel):
    message: str


class NestingPydanticMessage(BaseModel):
    message: str
    nested: PydanticMessage


@dataclass
class DataclassMessage:
    message: str


@dataclass
class NestingDataclassMessage:
    message: str
    nested: DataclassMessage


@dataclass
class NestingPydanticDataclassMessage:
    message: str
    nested: PydanticMessage


def test_pydantic() -> None:
    serde = Serialization()
    serde.add_serializer(try_get_known_serializers_for_type(PydanticMessage))

    message = PydanticMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert name == "PydanticMessage"
    assert json == b'{"message":"hello"}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_nested_pydantic() -> None:
    serde = Serialization()
    serde.add_serializer(try_get_known_serializers_for_type(NestingPydanticMessage))

    message = NestingPydanticMessage(message="hello", nested=PydanticMessage(message="world"))
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert json == b'{"message":"hello","nested":{"message":"world"}}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_dataclass() -> None:
    serde = Serialization()
    serde.add_serializer(try_get_known_serializers_for_type(DataclassMessage))

    message = DataclassMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert json == b'{"message": "hello"}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_nesting_dataclass_dataclass() -> None:
    serde = Serialization()
    serde.add_serializer(try_get_known_serializers_for_type(NestingDataclassMessage))

    message = NestingDataclassMessage(message="hello", nested=DataclassMessage(message="world"))
    name = serde.type_name(message)
    with pytest.raises(ValueError):
        _json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)


def test_nesting_dataclass_pydantic() -> None:
    serde = Serialization()
    serde.add_serializer(try_get_known_serializers_for_type(NestingPydanticDataclassMessage))

    message = NestingPydanticDataclassMessage(message="hello", nested=PydanticMessage(message="world"))
    name = serde.type_name(message)
    with pytest.raises(ValueError):
        _json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)


def test_invalid_type() -> None:
    serde = Serialization()
    try:
        serde.add_serializer(try_get_known_serializers_for_type(str))
    except ValueError as e:
        assert str(e) == "Unsupported type <class 'str'>"


def test_custom_type() -> None:
    serde = Serialization()

    class CustomStringTypeSerializer(MessageSerializer[str]):
        @property
        def data_content_type(self) -> str:
            return "str"

        @property
        def type_name(self) -> str:
            return "custom_str"

        def deserialize(self, payload: bytes) -> str:
            message = payload.decode("utf-8")
            return message[1:-1]

        def serialize(self, message: str) -> bytes:
            return f'"{message}"'.encode("utf-8")

    serde.add_serializer(CustomStringTypeSerializer())
    message = "hello"
    json = serde.serialize(message, type_name="custom_str", data_content_type="str")
    assert json == b'"hello"'
    deserialized = serde.deserialize(json, type_name="custom_str", data_content_type="str")
    assert deserialized == message
