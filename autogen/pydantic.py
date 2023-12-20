from typing import Any, Dict, Type

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION

__all__ = ("JsonSchemaValue", "model_dump", "model_dump_json", "type2schema")

PYDANTIC_V1 = PYDANTIC_VERSION.startswith("1.")

if not PYDANTIC_V1:
    from pydantic import TypeAdapter
    from pydantic.json_schema import JsonSchemaValue

    def type2schema(t: Type) -> JsonSchemaValue:
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
else:
    from pydantic import schema_of

    JsonSchemaValue = Dict[str, Any]

    def type2schema(t: Type) -> JsonSchemaValue:
        """Convert a type to a JSON schema

        Args:
            t (Type): The type to convert

        Returns:
            JsonSchemaValue: The JSON schema
        """
        d = schema_of(t)
        if "title" in d:
            d.pop("title")
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
