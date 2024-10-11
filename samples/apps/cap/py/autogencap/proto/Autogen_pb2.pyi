from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataMap(_message.Message):
    __slots__ = ("data",)

    class DataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

    DATA_FIELD_NUMBER: _ClassVar[int]
    data: _containers.ScalarMap[str, str]
    def __init__(self, data: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ReceiveReq(_message.Message):
    __slots__ = ("data_map", "data", "sender", "request_reply", "silent")
    DATA_MAP_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    REQUEST_REPLY_FIELD_NUMBER: _ClassVar[int]
    SILENT_FIELD_NUMBER: _ClassVar[int]
    data_map: DataMap
    data: str
    sender: str
    request_reply: bool
    silent: bool
    def __init__(
        self,
        data_map: _Optional[_Union[DataMap, _Mapping]] = ...,
        data: _Optional[str] = ...,
        sender: _Optional[str] = ...,
        request_reply: bool = ...,
        silent: bool = ...,
    ) -> None: ...

class Terminate(_message.Message):
    __slots__ = ("sender",)
    SENDER_FIELD_NUMBER: _ClassVar[int]
    sender: str
    def __init__(self, sender: _Optional[str] = ...) -> None: ...

class GenReplyReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenReplyResp(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: str
    def __init__(self, data: _Optional[str] = ...) -> None: ...

class PrepChat(_message.Message):
    __slots__ = ("recipient", "clear_history", "prepare_recipient")
    RECIPIENT_FIELD_NUMBER: _ClassVar[int]
    CLEAR_HISTORY_FIELD_NUMBER: _ClassVar[int]
    PREPARE_RECIPIENT_FIELD_NUMBER: _ClassVar[int]
    recipient: str
    clear_history: bool
    prepare_recipient: bool
    def __init__(
        self, recipient: _Optional[str] = ..., clear_history: bool = ..., prepare_recipient: bool = ...
    ) -> None: ...
