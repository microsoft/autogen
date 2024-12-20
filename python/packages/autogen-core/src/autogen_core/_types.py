from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


# TODO: Make this xlang friendly
@dataclass
class RpcNoneResponse:
    pass


@dataclass
class RpcMessageDroppedResponse:
    message_id: str


@dataclass
class CantHandleMessageResponse:
    message_id: str


@dataclass
class CancelRpc:
    pass


@dataclass
class CancelledRpc:
    pass
