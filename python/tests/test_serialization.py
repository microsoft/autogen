#custom type

from pydantic import BaseModel
from dataclasses import dataclass

import pytest

from agnext.core import Serialization

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
    serde.add_type(PydanticMessage)

    message = PydanticMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name)
    assert name == "PydanticMessage"
    assert json == '{"message":"hello"}'
    deserialized = serde.deserialize(json, type_name=name)
    assert deserialized == message

def test_nested_pydantic() -> None:
    serde = Serialization()
    serde.add_type(NestingPydanticMessage)

    message = NestingPydanticMessage(message="hello", nested=PydanticMessage(message="world"))
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name)
    assert json == '{"message":"hello","nested":{"message":"world"}}'
    deserialized = serde.deserialize(json, type_name=name)
    assert deserialized == message

def test_dataclass() -> None:
    serde = Serialization()
    serde.add_type(DataclassMessage)

    message = DataclassMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name)
    assert json == '{"message": "hello"}'
    deserialized = serde.deserialize(json, type_name=name)
    assert deserialized == message

def test_nesting_dataclass_dataclass() -> None:
    serde = Serialization()
    serde.add_type(NestingDataclassMessage)

    message = NestingDataclassMessage(message="hello", nested=DataclassMessage(message="world"))
    name = serde.type_name(message)
    with pytest.raises(ValueError):
        _json = serde.serialize(message, type_name=name)

def test_nesting_dataclass_pydantic() -> None:
    serde = Serialization()
    serde.add_type(NestingPydanticDataclassMessage)

    message = NestingPydanticDataclassMessage(message="hello", nested=PydanticMessage(message="world"))
    name = serde.type_name(message)
    with pytest.raises(ValueError):
        _json = serde.serialize(message, type_name=name)

def test_invalid_type() -> None:
    serde = Serialization()
    try:
        serde.add_type(str) # type: ignore
    except ValueError as e:
        assert str(e) == "Unsupported type <class 'str'>"

def test_custom_type() -> None:
    serde = Serialization()

    class CustomStringTypeDeserializer:
        def deserialize(self, message: str) -> str:
            return message[1:-1]

    class CustomStringTypeSerializer:
        def serialize(self, message: str) -> str:
            return f'"{message}"'

    serde.add_type_custom("custom_str", CustomStringTypeDeserializer(), CustomStringTypeSerializer())
    message = "hello"
    json = serde.serialize(message, type_name="custom_str")
    assert json == '"hello"'
    deserialized = serde.deserialize(json, type_name="custom_str")
    assert deserialized == message