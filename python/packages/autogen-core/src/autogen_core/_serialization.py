import json
from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar, Dict, List, Protocol, Sequence, TypeVar, cast, get_args, get_origin, runtime_checkable

from google.protobuf import any_pb2
from google.protobuf.message import Message
from pydantic import BaseModel

from ._type_helpers import is_union

T = TypeVar("T")


class MessageSerializer(Protocol[T]):
    @property
    def data_content_type(self) -> str: ...

    @property
    def type_name(self) -> str: ...

    def deserialize(self, payload: bytes) -> T: ...

    def serialize(self, message: T) -> bytes: ...


@runtime_checkable
class IsDataclass(Protocol):
    # as already noted in comments, checking for this attribute is currently
    # the most reliable way to ascertain that something is a dataclass
    __dataclass_fields__: ClassVar[Dict[str, Any]]


def is_dataclass(cls: type[Any]) -> bool:
    return hasattr(cls, "__dataclass_fields__")


def has_nested_dataclass(cls: type[IsDataclass]) -> bool:
    # iterate fields and check if any of them are dataclasses
    return any(is_dataclass(f.type) for f in cls.__dataclass_fields__.values())


def contains_a_union(cls: type[IsDataclass]) -> bool:
    return any(is_union(f.type) for f in cls.__dataclass_fields__.values())


def has_nested_base_model(cls: type[IsDataclass]) -> bool:
    for f in fields(cls):
        field_type = f.type
        # Resolve forward references and other annotations
        origin = get_origin(field_type)
        args = get_args(field_type)

        # If the field type is directly a subclass of BaseModel
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return True

        # If the field type is a generic type like List[BaseModel], Tuple[BaseModel, ...], etc.
        if origin is not None and args:
            for arg in args:
                # Recursively check the argument types
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return True
                elif get_origin(arg) is not None:
                    # Handle nested generics like List[List[BaseModel]]
                    if has_nested_base_model_in_type(arg):
                        return True
        # Handle Union types
        elif args:
            for arg in args:
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return True
                elif get_origin(arg) is not None:
                    if has_nested_base_model_in_type(arg):
                        return True
    return False


def has_nested_base_model_in_type(tp: Any) -> bool:
    """Helper function to check if a type or its arguments is a BaseModel subclass."""
    origin = get_origin(tp)
    args = get_args(tp)

    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return True
    if origin is not None and args:
        for arg in args:
            if has_nested_base_model_in_type(arg):
                return True
    return False


DataclassT = TypeVar("DataclassT", bound=IsDataclass)

JSON_DATA_CONTENT_TYPE = "application/json"
# TODO: what's the correct content type? There seems to be some disagreement over what it should be
PROTOBUF_DATA_CONTENT_TYPE = "application/x-protobuf"


class DataclassJsonMessageSerializer(MessageSerializer[DataclassT]):
    def __init__(self, cls: type[DataclassT]) -> None:
        if contains_a_union(cls):
            raise ValueError("Dataclass has a union type, which is not supported. To use a union, use a Pydantic model")

        if has_nested_dataclass(cls) or has_nested_base_model(cls):
            raise ValueError(
                "Dataclass has nested dataclasses or base models, which are not supported. To use nested types, use a Pydantic model"
            )

        self.cls = cls

    @property
    def data_content_type(self) -> str:
        return JSON_DATA_CONTENT_TYPE

    @property
    def type_name(self) -> str:
        return _type_name(self.cls)

    def deserialize(self, payload: bytes) -> DataclassT:
        message_str = payload.decode("utf-8")
        return self.cls(**json.loads(message_str))

    def serialize(self, message: DataclassT) -> bytes:
        return json.dumps(asdict(message)).encode("utf-8")


PydanticT = TypeVar("PydanticT", bound=BaseModel)


class PydanticJsonMessageSerializer(MessageSerializer[PydanticT]):
    def __init__(self, cls: type[PydanticT]) -> None:
        self.cls = cls

    @property
    def data_content_type(self) -> str:
        return JSON_DATA_CONTENT_TYPE

    @property
    def type_name(self) -> str:
        return _type_name(self.cls)

    def deserialize(self, payload: bytes) -> PydanticT:
        message_str = payload.decode("utf-8")
        return self.cls.model_validate_json(message_str)

    def serialize(self, message: PydanticT) -> bytes:
        return message.model_dump_json().encode("utf-8")


ProtobufT = TypeVar("ProtobufT", bound=Message)


# This class serializes to and from a google.protobuf.Any message that has been serialized to a string
class ProtobufMessageSerializer(MessageSerializer[ProtobufT]):
    def __init__(self, cls: type[ProtobufT]) -> None:
        self.cls = cls

    @property
    def data_content_type(self) -> str:
        return PROTOBUF_DATA_CONTENT_TYPE

    @property
    def type_name(self) -> str:
        return _type_name(self.cls)

    def deserialize(self, payload: bytes) -> ProtobufT:
        # Parse payload into a proto any
        any_proto = any_pb2.Any()
        any_proto.ParseFromString(payload)

        destination_message = self.cls()

        if not any_proto.Unpack(destination_message):  # type: ignore
            raise ValueError(f"Failed to unpack payload into {self.cls}")

        return destination_message

    def serialize(self, message: ProtobufT) -> bytes:
        any_proto = any_pb2.Any()
        any_proto.Pack(message)  # type: ignore
        return any_proto.SerializeToString()


@dataclass
class UnknownPayload:
    type_name: str
    data_content_type: str
    payload: bytes


def _type_name(cls: type[Any] | Any) -> str:
    if isinstance(cls, type):
        return cls.__name__
    else:
        return cast(str, cls.__class__.__name__)


V = TypeVar("V")


def try_get_known_serializers_for_type(cls: type[Any]) -> list[MessageSerializer[Any]]:
    """:meta private:"""

    serializers: List[MessageSerializer[Any]] = []
    if issubclass(cls, BaseModel):
        serializers.append(PydanticJsonMessageSerializer(cls))
    elif is_dataclass(cls):
        serializers.append(DataclassJsonMessageSerializer(cls))
    elif issubclass(cls, Message):
        serializers.append(ProtobufMessageSerializer(cls))

    return serializers


class SerializationRegistry:
    """:meta private:"""

    def __init__(self) -> None:
        # type_name, data_content_type -> serializer
        self._serializers: dict[tuple[str, str], MessageSerializer[Any]] = {}

    def add_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        if isinstance(serializer, Sequence):
            for c in serializer:
                self.add_serializer(c)
            return

        self._serializers[(serializer.type_name, serializer.data_content_type)] = serializer

    def deserialize(self, payload: bytes, *, type_name: str, data_content_type: str) -> Any:
        serializer = self._serializers.get((type_name, data_content_type))
        if serializer is None:
            return UnknownPayload(type_name, data_content_type, payload)

        return serializer.deserialize(payload)

    def serialize(self, message: Any, *, type_name: str, data_content_type: str) -> bytes:
        serializer = self._serializers.get((type_name, data_content_type))
        if serializer is None:
            raise ValueError(f"Unknown type {type_name} with content type {data_content_type}")

        return serializer.serialize(message)

    def is_registered(self, type_name: str, data_content_type: str) -> bool:
        return (type_name, data_content_type) in self._serializers

    def type_name(self, message: Any) -> str:
        return _type_name(message)
