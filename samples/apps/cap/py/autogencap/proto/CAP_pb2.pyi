from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActorProperties(_message.Message):
    __slots__ = ("dict",)
    class DictEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DICT_FIELD_NUMBER: _ClassVar[int]
    dict: _containers.ScalarMap[str, str]
    def __init__(self, dict: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ActorInfo(_message.Message):
    __slots__ = ("name", "namespace", "description", "properties")
    NAME_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    name: str
    namespace: str
    description: str
    properties: ActorProperties
    def __init__(self, name: _Optional[str] = ..., namespace: _Optional[str] = ..., description: _Optional[str] = ..., properties: _Optional[_Union[ActorProperties, _Mapping]] = ...) -> None: ...

class ActorRegistration(_message.Message):
    __slots__ = ("actor_info",)
    ACTOR_INFO_FIELD_NUMBER: _ClassVar[int]
    actor_info: ActorInfo
    def __init__(self, actor_info: _Optional[_Union[ActorInfo, _Mapping]] = ...) -> None: ...

class ActorLookup(_message.Message):
    __slots__ = ("actor_info", "service_descriptor")
    ACTOR_INFO_FIELD_NUMBER: _ClassVar[int]
    SERVICE_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
    actor_info: ActorInfo
    service_descriptor: str
    def __init__(self, actor_info: _Optional[_Union[ActorInfo, _Mapping]] = ..., service_descriptor: _Optional[str] = ...) -> None: ...
