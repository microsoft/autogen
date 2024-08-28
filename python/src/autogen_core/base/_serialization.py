import json
from dataclasses import asdict
from typing import Any, ClassVar, Dict, Protocol, TypeVar, cast, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class IsDataclass(Protocol):
    # as already noted in comments, checking for this attribute is currently
    # the most reliable way to ascertain that something is a dataclass
    __dataclass_fields__: ClassVar[Dict[str, Any]]


def is_dataclass(cls: type[Any]) -> bool:
    return isinstance(cls, IsDataclass)


def has_nested_dataclass(cls: type[IsDataclass]) -> bool:
    # iterate fields and check if any of them are dataclasses
    return any(is_dataclass(f.type) for f in cls.__dataclass_fields__.values())


def has_nested_base_model(cls: type[IsDataclass]) -> bool:
    # iterate fields and check if any of them are basebodels
    return any(issubclass(f.type, BaseModel) for f in cls.__dataclass_fields__.values())


T = TypeVar("T", covariant=True)


class TypeDeserializer(Protocol[T]):
    def deserialize(self, message: str) -> T: ...


U = TypeVar("U", contravariant=True)


class TypeSerializer(Protocol[U]):
    def serialize(self, message: U) -> str: ...


DataclassT = TypeVar("DataclassT", bound=IsDataclass)


class DataclassTypeDeserializer(TypeDeserializer[DataclassT]):
    def __init__(self, cls: type[DataclassT]) -> None:
        self.cls = cls

    def deserialize(self, message: str) -> DataclassT:
        return self.cls(**json.loads(message))


class DataclassTypeSerializer(TypeSerializer[IsDataclass]):
    def serialize(self, message: IsDataclass) -> str:
        if has_nested_dataclass(type(message)) or has_nested_base_model(type(message)):
            raise ValueError("Dataclass has nested dataclasses or base models, which are not supported")

        return json.dumps(asdict(message))


PydanticT = TypeVar("PydanticT", bound=BaseModel)


class PydanticTypeDeserializer(TypeDeserializer[PydanticT]):
    def __init__(self, cls: type[PydanticT]) -> None:
        self.cls = cls

    def deserialize(self, message: str) -> PydanticT:
        return self.cls.model_validate_json(message)


class PydanticTypeSerializer(TypeSerializer[BaseModel]):
    def serialize(self, message: BaseModel) -> str:
        return message.model_dump_json()


def _type_name(cls: type[Any] | Any) -> str:
    if isinstance(cls, type):
        return cls.__name__
    else:
        return cast(str, cls.__class__.__name__)


V = TypeVar("V")


class Serialization:
    def __init__(self) -> None:
        self._deserializers: Dict[str, TypeDeserializer[Any]] = {}
        self._serializers: Dict[str, TypeSerializer[Any]] = {}

    def add_type(self, message_type: type[BaseModel] | type[IsDataclass]) -> None:
        if issubclass(message_type, BaseModel):
            self.add_type_custom(
                _type_name(message_type), PydanticTypeDeserializer(message_type), PydanticTypeSerializer()
            )
        elif isinstance(message_type, IsDataclass):
            self.add_type_custom(
                _type_name(message_type), DataclassTypeDeserializer(message_type), DataclassTypeSerializer()
            )
        else:
            raise ValueError(f"Unsupported type {message_type}")

    def add_type_custom(self, type_name: str, deserializer: TypeDeserializer[V], serializer: TypeSerializer[V]) -> None:
        self._deserializers[type_name] = deserializer
        self._serializers[type_name] = serializer

    def deserialize(self, message: str, *, type_name: str) -> Any:
        return self._deserializers[type_name].deserialize(message)

    def type_name(self, message: Any) -> str:
        return _type_name(message)

    def serialize(self, message: Any, *, type_name: str) -> str:
        return self._serializers[type_name].serialize(message)

    def is_registered(self, type_name: str) -> bool:
        return type_name in self._deserializers


MESSAGE_TYPE_REGISTRY = Serialization()
