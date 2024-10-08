from collections.abc import Sequence
from types import NoneType, UnionType
from typing import Any, Optional, Tuple, Type, Union, get_args, get_origin

# Had to redefine this from grpc.aio._typing as using that one was causing mypy errors
ChannelArgumentType = Sequence[Tuple[str, Any]]


def is_union(t: object) -> bool:
    origin = get_origin(t)
    return origin is Union or origin is UnionType


def is_optional(t: object) -> bool:
    origin = get_origin(t)
    return origin is Optional


# Special type to avoid the 3.10 vs 3.11+ difference of typing._SpecialForm vs typing.Any
class AnyType:
    pass


def get_types(t: object) -> Sequence[Type[Any]] | None:
    if is_union(t):
        return get_args(t)
    elif is_optional(t):
        return tuple(list(get_args(t)) + [NoneType])
    elif t is Any:
        return (AnyType,)
    elif isinstance(t, type):
        return (t,)
    elif isinstance(t, NoneType):
        return (NoneType,)
    else:
        return None
