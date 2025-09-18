import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Dict, ForwardRef, List, Literal, Optional, Type, Union, cast

from pydantic import (
    UUID1,
    UUID3,
    UUID4,
    UUID5,
    AnyUrl,
    BaseModel,
    EmailStr,
    Field,
    Json,
    conbytes,
    confloat,
    conint,
    conlist,
    constr,
    create_model,
)
from pydantic.fields import FieldInfo


class SchemaConversionError(Exception):
    """Base class for schema conversion exceptions."""

    pass


class ReferenceNotFoundError(SchemaConversionError):
    """Raised when a $ref cannot be resolved."""

    pass


class FormatNotSupportedError(SchemaConversionError):
    """Raised when a format is not supported."""

    pass


class UnsupportedKeywordError(SchemaConversionError):
    """Raised when an unsupported JSON Schema keyword is encountered."""

    pass


TYPE_MAPPING: Dict[str, Type[Any]] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
    "array": List,
    "object": dict,
    "null": type(None),
}

FORMAT_MAPPING: Dict[str, Any] = {
    "uuid": UUID4,
    "uuid1": UUID1,
    "uuid2": UUID4,
    "uuid3": UUID3,
    "uuid4": UUID4,
    "uuid5": UUID5,
    "email": EmailStr,
    "uri": AnyUrl,
    "hostname": constr(strict=True),
    "ipv4": IPv4Address,
    "ipv6": IPv6Address,
    "ipv4-network": IPv4Address,
    "ipv6-network": IPv6Address,
    "date-time": datetime.datetime,
    "date": datetime.date,
    "time": datetime.time,
    "duration": datetime.timedelta,
    "int32": conint(strict=True, ge=-(2**31), le=2**31 - 1),
    "int64": conint(strict=True, ge=-(2**63), le=2**63 - 1),
    "float": confloat(strict=True),
    "double": float,
    "decimal": float,
    "byte": conbytes(strict=True),
    "binary": conbytes(strict=True),
    "password": str,
    "path": str,
    "json": Json,
}


def _make_field(
    default: Any,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    """Construct a Pydantic Field with proper typing."""
    field_kwargs: Dict[str, Any] = {}
    if title is not None:
        field_kwargs["title"] = title
    if description is not None:
        field_kwargs["description"] = description
    return Field(default, **field_kwargs)


class _JSONSchemaToPydantic:
    def __init__(self) -> None:
        self._model_cache: Dict[str, Optional[Union[Type[BaseModel], ForwardRef]]] = {}

    def _resolve_ref(self, ref: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        ref_key = ref.split("/")[-1]
        definitions = cast(dict[str, dict[str, Any]], schema.get("$defs", {}))

        if ref_key not in definitions:
            raise ReferenceNotFoundError(
                f"Reference `{ref}` not found in `$defs`. Available keys: {list(definitions.keys())}"
            )

        return definitions[ref_key]

    def get_ref(self, ref_name: str) -> Any:
        if ref_name not in self._model_cache:
            raise ReferenceNotFoundError(
                f"Reference `{ref_name}` not found in cache. Available: {list(self._model_cache.keys())}"
            )

        if self._model_cache[ref_name] is None:
            return ForwardRef(ref_name)

        return self._model_cache[ref_name]

    def _get_item_model_name(self, array_field_name: str, parent_model_name: str) -> str:
        """Generate hash-based model names for array items to keep names short and unique."""
        import hashlib

        # Create a short hash of the full path to ensure uniqueness
        full_path = f"{parent_model_name}_{array_field_name}"
        hash_suffix = hashlib.md5(full_path.encode()).hexdigest()[:6]

        # Use field name as-is with hash suffix
        return f"{array_field_name}_{hash_suffix}"

    def _process_definitions(self, root_schema: Dict[str, Any]) -> None:
        if "$defs" in root_schema:
            for model_name in root_schema["$defs"]:
                if model_name not in self._model_cache:
                    self._model_cache[model_name] = None

            for model_name, model_schema in root_schema["$defs"].items():
                if self._model_cache[model_name] is None:
                    self._model_cache[model_name] = self.json_schema_to_pydantic(model_schema, model_name, root_schema)

    def json_schema_to_pydantic(
        self, schema: Dict[str, Any], model_name: str = "GeneratedModel", root_schema: Optional[Dict[str, Any]] = None
    ) -> Type[BaseModel]:
        if root_schema is None:
            root_schema = schema
            self._process_definitions(root_schema)

        if "$ref" in schema:
            resolved = self._resolve_ref(schema["$ref"], root_schema)
            schema = {**resolved, **{k: v for k, v in schema.items() if k != "$ref"}}

        if "allOf" in schema:
            merged: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
            for s in schema["allOf"]:
                part = self._resolve_ref(s["$ref"], root_schema) if "$ref" in s else s
                merged["properties"].update(part.get("properties", {}))
                merged["required"].extend(part.get("required", []))
            for k, v in schema.items():
                if k not in {"allOf", "properties", "required"}:
                    merged[k] = v
            merged["required"] = list(set(merged["required"]))
            schema = merged

        return self._json_schema_to_model(schema, model_name, root_schema)

    def _resolve_union_types(self, schemas: List[Dict[str, Any]]) -> List[Any]:
        types: List[Any] = []
        for s in schemas:
            if "$ref" in s:
                types.append(self.get_ref(s["$ref"].split("/")[-1]))
            elif "enum" in s:
                types.append(Literal[tuple(s["enum"])] if len(s["enum"]) > 0 else Any)
            else:
                json_type = s.get("type")
                if json_type not in TYPE_MAPPING:
                    raise UnsupportedKeywordError(f"Unsupported or missing type `{json_type}` in union")

                # Handle array types with items specification
                if json_type == "array" and "items" in s:
                    item_schema = s["items"]
                    if "$ref" in item_schema:
                        item_type = self.get_ref(item_schema["$ref"].split("/")[-1])
                    else:
                        item_type_name = item_schema.get("type")
                        if item_type_name is None:
                            item_type = str
                        elif item_type_name not in TYPE_MAPPING:
                            raise UnsupportedKeywordError(f"Unsupported item type `{item_type_name}` in union array")
                        else:
                            item_type = TYPE_MAPPING[item_type_name]

                    constraints = {}
                    if "minItems" in s:
                        constraints["min_length"] = s["minItems"]
                    if "maxItems" in s:
                        constraints["max_length"] = s["maxItems"]

                    array_type = conlist(item_type, **constraints) if constraints else List[item_type]  # type: ignore[valid-type]
                    types.append(array_type)
                else:
                    types.append(TYPE_MAPPING[json_type])
        return types

    def _extract_field_type(self, key: str, value: Dict[str, Any], model_name: str, root_schema: Dict[str, Any]) -> Any:
        json_type = value.get("type")
        if json_type not in TYPE_MAPPING:
            raise UnsupportedKeywordError(
                f"Unsupported or missing type `{json_type}` for field `{key}` in `{model_name}`"
            )

        base_type = TYPE_MAPPING[json_type]
        constraints: Dict[str, Any] = {}

        if json_type == "string":
            if "minLength" in value:
                constraints["min_length"] = value["minLength"]
            if "maxLength" in value:
                constraints["max_length"] = value["maxLength"]
            if "pattern" in value:
                constraints["pattern"] = value["pattern"]
            if constraints:
                base_type = constr(**constraints)

        elif json_type == "integer":
            if "minimum" in value:
                constraints["ge"] = value["minimum"]
            if "maximum" in value:
                constraints["le"] = value["maximum"]
            if "exclusiveMinimum" in value:
                constraints["gt"] = value["exclusiveMinimum"]
            if "exclusiveMaximum" in value:
                constraints["lt"] = value["exclusiveMaximum"]
            if constraints:
                base_type = conint(**constraints)

        elif json_type == "number":
            if "minimum" in value:
                constraints["ge"] = value["minimum"]
            if "maximum" in value:
                constraints["le"] = value["maximum"]
            if "exclusiveMinimum" in value:
                constraints["gt"] = value["exclusiveMinimum"]
            if "exclusiveMaximum" in value:
                constraints["lt"] = value["exclusiveMaximum"]
            if constraints:
                base_type = confloat(**constraints)

        elif json_type == "array":
            if "minItems" in value:
                constraints["min_length"] = value["minItems"]
            if "maxItems" in value:
                constraints["max_length"] = value["maxItems"]
            item_schema = value.get("items", {"type": "string"})
            if "$ref" in item_schema:
                item_type = self.get_ref(item_schema["$ref"].split("/")[-1])
            elif item_schema.get("type") == "object" and "properties" in item_schema:
                # Handle array items that are objects with properties - create a nested model
                # Use hash-based naming to keep names short and unique
                item_model_name = self._get_item_model_name(key, model_name)
                item_type = self._json_schema_to_model(item_schema, item_model_name, root_schema)
            else:
                item_type_name = item_schema.get("type")
                if item_type_name is None:
                    item_type = str
                elif item_type_name not in TYPE_MAPPING:
                    raise UnsupportedKeywordError(
                        f"Unsupported or missing item type `{item_type_name}` for array field `{key}` in `{model_name}`"
                    )
                else:
                    item_type = TYPE_MAPPING[item_type_name]

            base_type = conlist(item_type, **constraints) if constraints else List[item_type]  # type: ignore[valid-type]

        if "format" in value:
            format_type = FORMAT_MAPPING.get(value["format"])
            if format_type is None:
                raise FormatNotSupportedError(f"Unknown format `{value['format']}` for `{key}` in `{model_name}`")
            if not isinstance(format_type, type):
                return format_type
            if not issubclass(format_type, str):
                return format_type
            return format_type

        return base_type

    def _json_schema_to_model(
        self, schema: Dict[str, Any], model_name: str, root_schema: Dict[str, Any]
    ) -> Type[BaseModel]:
        if "allOf" in schema:
            merged: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
            for s in schema["allOf"]:
                part = self._resolve_ref(s["$ref"], root_schema) if "$ref" in s else s
                merged["properties"].update(part.get("properties", {}))
                merged["required"].extend(part.get("required", []))
            for k, v in schema.items():
                if k not in {"allOf", "properties", "required"}:
                    merged[k] = v
            merged["required"] = list(set(merged["required"]))
            schema = merged

        fields: Dict[str, tuple[Any, FieldInfo]] = {}
        required_fields = set(schema.get("required", []))

        for key, value in schema.get("properties", {}).items():
            if "$ref" in value:
                ref_name = value["$ref"].split("/")[-1]
                field_type = self.get_ref(ref_name)
            elif "anyOf" in value:
                sub_models = self._resolve_union_types(value["anyOf"])
                field_type = Union[tuple(sub_models)]
            elif "oneOf" in value:
                sub_models = self._resolve_union_types(value["oneOf"])
                field_type = Union[tuple(sub_models)]
                if "discriminator" in value:
                    discriminator = value["discriminator"]["propertyName"]
                    field_type = Annotated[field_type, Field(discriminator=discriminator)]
            elif "enum" in value:
                field_type = Literal[tuple(value["enum"])]
            elif "allOf" in value:
                merged = {"type": "object", "properties": {}, "required": []}
                for s in value["allOf"]:
                    part = self._resolve_ref(s["$ref"], root_schema) if "$ref" in s else s
                    merged["properties"].update(part.get("properties", {}))
                    merged["required"].extend(part.get("required", []))
                for k, v in value.items():
                    if k not in {"allOf", "properties", "required"}:
                        merged[k] = v
                merged["required"] = list(set(merged["required"]))
                field_type = self._json_schema_to_model(merged, f"{model_name}_{key}", root_schema)
            elif value.get("type") == "object" and "properties" in value:
                field_type = self._json_schema_to_model(value, f"{model_name}_{key}", root_schema)
            else:
                field_type = self._extract_field_type(key, value, model_name, root_schema)

            if field_type is None:
                raise UnsupportedKeywordError(f"Unsupported or missing type for field `{key}` in `{model_name}`")

            default_value = value.get("default")
            is_required = key in required_fields

            if not is_required and default_value is None:
                field_type = Optional[field_type]

            field_args = {
                "default": default_value if not is_required else ...,
            }
            if "title" in value:
                field_args["title"] = value["title"]
            if "description" in value:
                field_args["description"] = value["description"]

            fields[key] = (
                field_type,
                _make_field(
                    default_value if not is_required else ...,
                    title=value.get("title"),
                    description=value.get("description"),
                ),
            )

        model: Type[BaseModel] = create_model(model_name, **cast(dict[str, Any], fields))
        model.model_rebuild()
        return model


def schema_to_pydantic_model(schema: Dict[str, Any], model_name: str = "GeneratedModel") -> Type[BaseModel]:
    """
    Convert a JSON Schema dictionary to a fully-typed Pydantic model.

    This function handles schema translation and validation logic to produce
    a Pydantic model.

    **Supported JSON Schema Features**

    - **Primitive types**: `string`, `integer`, `number`, `boolean`, `object`, `array`, `null`
    - **String formats**:
        - `email`, `uri`, `uuid`, `uuid1`, `uuid3`, `uuid4`, `uuid5`
        - `hostname`, `ipv4`, `ipv6`, `ipv4-network`, `ipv6-network`
        - `date`, `time`, `date-time`, `duration`
        - `byte`, `binary`, `password`, `path`
    - **String constraints**:
        - `minLength`, `maxLength`, `pattern`
    - **Numeric constraints**:
        - `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`
    - **Array constraints**:
        - `minItems`, `maxItems`, `items`
    - **Object schema support**:
        - `properties`, `required`, `title`, `description`, `default`
    - **Enums**:
        - Converted to Python `Literal` type
    - **Union types**:
        - `anyOf`, `oneOf` supported with optional `discriminator`
    - **Inheritance and composition**:
        - `allOf` merges multiple schemas into one model
    - **$ref and $defs resolution**:
        - Supports references to sibling definitions and self-referencing schemas

    .. code-block:: python

        from autogen_core.utils import schema_to_pydantic_model

        # Example 1: Simple user model
        schema = {
            "title": "User",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name", "email"],
        }

        UserModel = schema_to_pydantic_model(schema)
        user = UserModel(name="Alice", email="alice@example.com", age=30)

    .. code-block:: python

        from autogen_core.utils import schema_to_pydantic_model

        # Example 2: Nested model
        schema = {
            "title": "BlogPost",
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "author": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "email": {"type": "string", "format": "email"}},
                    "required": ["name"],
                },
            },
            "required": ["title", "author"],
        }

        BlogPost = schema_to_pydantic_model(schema)


    .. code-block:: python

        from autogen_core.utils import schema_to_pydantic_model

        # Example 3: allOf merging with $refs
        schema = {
            "title": "EmployeeWithDepartment",
            "allOf": [{"$ref": "#/$defs/Employee"}, {"$ref": "#/$defs/Department"}],
            "$defs": {
                "Employee": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                    "required": ["id", "name"],
                },
                "Department": {
                    "type": "object",
                    "properties": {"department": {"type": "string"}},
                    "required": ["department"],
                },
            },
        }

        Model = schema_to_pydantic_model(schema)

    .. code-block:: python

        from autogen_core.utils import schema_to_pydantic_model

        # Example 4: Self-referencing (recursive) model
        schema = {
            "title": "Category",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "subcategories": {"type": "array", "items": {"$ref": "#/$defs/Category"}},
            },
            "required": ["name"],
            "$defs": {
                "Category": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "subcategories": {"type": "array", "items": {"$ref": "#/$defs/Category"}},
                    },
                    "required": ["name"],
                }
            },
        }

        Category = schema_to_pydantic_model(schema)

    .. code-block:: python

        # Example 5: Serializing and deserializing with Pydantic

        from uuid import uuid4
        from pydantic import BaseModel, EmailStr, Field
        from typing import Optional, List, Dict, Any
        from autogen_core.utils import schema_to_pydantic_model


        class Address(BaseModel):
            street: str
            city: str
            zipcode: str


        class User(BaseModel):
            id: str
            name: str
            email: EmailStr
            age: int = Field(..., ge=18)
            address: Address


        class Employee(BaseModel):
            id: str
            name: str
            manager: Optional["Employee"] = None


        class Department(BaseModel):
            name: str
            employees: List[Employee]


        class ComplexModel(BaseModel):
            user: User
            extra_info: Optional[Dict[str, Any]] = None
            sub_items: List[Employee]


        # Convert ComplexModel to JSON schema
        complex_schema = ComplexModel.model_json_schema()

        # Rebuild a new Pydantic model from JSON schema
        ReconstructedModel = schema_to_pydantic_model(complex_schema, "ComplexModel")

        # Instantiate reconstructed model
        reconstructed = ReconstructedModel(
            user={
                "id": str(uuid4()),
                "name": "Alice",
                "email": "alice@example.com",
                "age": 30,
                "address": {"street": "123 Main St", "city": "Wonderland", "zipcode": "12345"},
            },
            sub_items=[{"id": str(uuid4()), "name": "Bob", "manager": {"id": str(uuid4()), "name": "Eve"}}],
        )

        print(reconstructed.model_dump())


    Args:
        schema (Dict[str, Any]): A valid JSON Schema dictionary.
        model_name (str, optional): The name of the root model. Defaults to "GeneratedModel".

    Returns:
        Type[BaseModel]: A dynamically generated Pydantic model class.

    Raises:
        ReferenceNotFoundError: If a `$ref` key references a missing entry.
        FormatNotSupportedError: If a `format` keyword is unknown or unsupported.
        UnsupportedKeywordError: If the schema contains an unsupported `type`.

    See Also:
        - :class:`pydantic.BaseModel`
        - :func:`pydantic.create_model`
        - https://json-schema.org/
    """
    ...

    return _JSONSchemaToPydantic().json_schema_to_pydantic(schema, model_name)
