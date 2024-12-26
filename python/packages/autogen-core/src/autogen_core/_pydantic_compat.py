# File based from: https://github.com/microsoft/autogen/blob/47f905267245e143562abfb41fcba503a9e1d56d/autogen/_pydantic.py
# Credit to original authors


from typing import Any, Dict, Tuple, Type, Union, get_args

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION
from typing_extensions import get_origin

__all__ = ("model_dump", "type2schema")

PYDANTIC_V1 = PYDANTIC_VERSION.startswith("1.")


def type2schema(t: Type[Any] | None) -> Dict[str, Any]:
    if PYDANTIC_V1:
        from pydantic import schema_of  # type: ignore

        if t is None:
            return {"type": "null"}
        elif get_origin(t) is Union:
            return {"anyOf": [type2schema(tt) for tt in get_args(t)]}
        elif get_origin(t) in [Tuple, tuple]:
            prefixItems = [type2schema(tt) for tt in get_args(t)]
            return {
                "maxItems": len(prefixItems),
                "minItems": len(prefixItems),
                "prefixItems": prefixItems,
                "type": "array",
            }

        d = schema_of(t)  # type: ignore
        if "title" in d:
            d.pop("title")
        if "description" in d:
            d.pop("description")

        return d
    else:
        from pydantic import TypeAdapter

        return TypeAdapter(t).json_schema()


def model_dump(model: BaseModel) -> Dict[str, Any]:
    if PYDANTIC_V1:
        return model.dict()  # type: ignore
    else:
        return model.model_dump()
