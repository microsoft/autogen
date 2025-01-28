from dataclasses import dataclass
from typing import Union

import pytest
from autogen_core import Image
from autogen_core._serialization import (
    JSON_DATA_CONTENT_TYPE,
    PROTOBUF_DATA_CONTENT_TYPE,
    DataclassJsonMessageSerializer,
    MessageSerializer,
    PydanticJsonMessageSerializer,
    SerializationRegistry,
    try_get_known_serializers_for_type,
)
from PIL import Image as PILImage
from protos.serialization_test_pb2 import NestingProtoMessage, ProtoMessage
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
    serde = SerializationRegistry()
    serde.add_serializer(try_get_known_serializers_for_type(PydanticMessage))

    message = PydanticMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert name == "PydanticMessage"
    assert json == b'{"message":"hello"}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_nested_pydantic() -> None:
    serde = SerializationRegistry()
    serde.add_serializer(try_get_known_serializers_for_type(NestingPydanticMessage))

    message = NestingPydanticMessage(message="hello", nested=PydanticMessage(message="world"))
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert json == b'{"message":"hello","nested":{"message":"world"}}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_dataclass() -> None:
    serde = SerializationRegistry()
    serde.add_serializer(try_get_known_serializers_for_type(DataclassMessage))

    message = DataclassMessage(message="hello")
    name = serde.type_name(message)
    json = serde.serialize(message, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert json == b'{"message": "hello"}'
    deserialized = serde.deserialize(json, type_name=name, data_content_type=JSON_DATA_CONTENT_TYPE)
    assert deserialized == message


def test_nesting_dataclass_dataclass() -> None:
    serde = SerializationRegistry()
    with pytest.raises(ValueError):
        serde.add_serializer(try_get_known_serializers_for_type(NestingDataclassMessage))


def test_proto() -> None:
    serde = SerializationRegistry()
    serde.add_serializer(try_get_known_serializers_for_type(ProtoMessage))

    message = ProtoMessage(message="hello")
    name = serde.type_name(message)
    data = serde.serialize(message, type_name=name, data_content_type=PROTOBUF_DATA_CONTENT_TYPE)
    assert name == "ProtoMessage"
    deserialized = serde.deserialize(data, type_name=name, data_content_type=PROTOBUF_DATA_CONTENT_TYPE)
    assert deserialized.message == message.message


def test_nested_proto() -> None:
    serde = SerializationRegistry()
    serde.add_serializer(try_get_known_serializers_for_type(NestingProtoMessage))

    message = NestingProtoMessage(message="hello", nested=ProtoMessage(message="world"))
    name = serde.type_name(message)
    data = serde.serialize(message, type_name=name, data_content_type=PROTOBUF_DATA_CONTENT_TYPE)
    deserialized = serde.deserialize(data, type_name=name, data_content_type=PROTOBUF_DATA_CONTENT_TYPE)
    assert deserialized.message == message.message
    assert deserialized.nested.message == message.nested.message


@dataclass
class DataclassNestedUnionSyntaxOldMessage:
    message: Union[str, int]


@dataclass
class DataclassNestedUnionSyntaxNewMessage:
    message: str | int


@pytest.mark.parametrize("cls", [DataclassNestedUnionSyntaxOldMessage, DataclassNestedUnionSyntaxNewMessage])
def test_nesting_union_old_syntax_dataclass(
    cls: type[DataclassNestedUnionSyntaxOldMessage | DataclassNestedUnionSyntaxNewMessage],
) -> None:
    with pytest.raises(ValueError):
        _serializer = DataclassJsonMessageSerializer(cls)


def test_nesting_dataclass_pydantic() -> None:
    serde = SerializationRegistry()
    with pytest.raises(ValueError):
        serde.add_serializer(try_get_known_serializers_for_type(NestingPydanticDataclassMessage))


def test_invalid_type() -> None:
    serde = SerializationRegistry()
    try:
        serde.add_serializer(try_get_known_serializers_for_type(str))
    except ValueError as e:
        assert str(e) == "Unsupported type <class 'str'>"


def test_custom_type() -> None:
    serde = SerializationRegistry()

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


def test_image_type() -> None:
    pil_image = PILImage.new("RGB", (100, 100))

    image = Image(pil_image)

    class PydanticImageMessage(BaseModel):
        image: Image

    serializer = PydanticJsonMessageSerializer(PydanticImageMessage)

    json = serializer.serialize(PydanticImageMessage(image=image))

    deserialized = serializer.deserialize(json)

    assert deserialized.image.image.size == (100, 100)
    assert deserialized.image.image.mode == "RGB"
    assert deserialized.image.image == image.image
