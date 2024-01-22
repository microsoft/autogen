from typing import Any, Dict, Optional, Tuple, Type, Union, get_args

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION
from typing_extensions import get_origin

__all__ = ("JsonSchemaValue", "model_dump", "model_dump_json", "type2schema", "evaluate_forwardref")

PYDANTIC_V1 = PYDANTIC_VERSION.startswith("1.")

if not PYDANTIC_V1:
    from pydantic import TypeAdapter
    from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref
    from pydantic.json_schema import JsonSchemaValue

    def type2schema(t: Optional[Type]) -> JsonSchemaValue:
        """Convert a type to a JSON schema

        Args:
            t (Type): The type to convert

        Returns:
            JsonSchemaValue: The JSON schema
        """
        return TypeAdapter(t).json_schema()

    def model_dump(model: BaseModel) -> Dict[str, Any]:
        """Convert a pydantic model to a dict

        Args:
            model (BaseModel): The model to convert

        Returns:
            Dict[str, Any]: The dict representation of the model

        """
        return model.model_dump()

    def model_dump_json(model: BaseModel) -> str:
        """Convert a pydantic model to a JSON string

        Args:
            model (BaseModel): The model to convert

        Returns:
            str: The JSON string representation of the model
        """
        return model.model_dump_json()


# Remove this once we drop support for pydantic 1.x
else:  # pragma: no cover
    from pydantic import schema_of
    from pydantic.typing import evaluate_forwardref as evaluate_forwardref

    JsonSchemaValue = Dict[str, Any]

    def type2schema(t: Optional[Type]) -> JsonSchemaValue:
        """Convert a type to a JSON schema

        Args:
            t (Type): The type to convert

        Returns:
            JsonSchemaValue: The JSON schema
        """
        if PYDANTIC_V1:
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

        d = schema_of(t)
        if "title" in d:
            d.pop("title")
        if "description" in d:
            d.pop("description")

        return d

    def model_dump(model: BaseModel) -> Dict[str, Any]:
        """Convert a pydantic model to a dict

        Args:
            model (BaseModel): The model to convert

        Returns:
            Dict[str, Any]: The dict representation of the model

        """
        return model.dict()

    def model_dump_json(model: BaseModel) -> str:
        """Convert a pydantic model to a JSON string

        Args:
            model (BaseModel): The model to convert

        Returns:
            str: The JSON string representation of the model
        """
        return model.json()
