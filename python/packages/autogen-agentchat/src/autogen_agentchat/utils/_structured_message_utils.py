import datetime
import logging
from typing import Any, Dict, ForwardRef, List, Optional, Type, Union

from pydantic import (
    UUID1,
    UUID3,
    UUID4,
    UUID5,
    AnyUrl,
    BaseModel,
    EmailStr,
    Field,
    IPvAnyAddress,
    conbytes,
    confloat,
    conint,
    constr,
    create_model,
)

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TYPE_MAPPING: Dict[str, Any] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
    "array": List,
    "object": dict,
    "null": None,
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
    "ipv4": IPvAnyAddress,
    "ipv6": IPvAnyAddress,
    "ipv4-network": IPvAnyAddress,
    "ipv6-network": IPvAnyAddress,
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
}


class JSONSchemaToPydantic:
    """Class to convert JSON Schema to Pydantic models with caching, recursion handling, and detailed logging."""

    def __init__(self):
        self._model_cache = {}  # Cache for models created from `$defs`
        self._defs_cache = {}  # Store final `$defs` models

    def _resolve_ref(self, ref: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves a `$ref` into the actual schema definition."""
        ref_key = ref.split("/")[-1]
        definitions = schema.get("$defs", {})

        if ref_key not in definitions:
            raise ValueError(
                f"[ERROR] Reference `{ref}` not found in `$defs`. Available keys: {list(definitions.keys())}"
            )

        logger.debug(f"[DEBUG] Resolved `$ref`: {ref} → `{ref_key}`")
        return definitions[ref_key]

    def get_ref(self, ref_name: str) -> Any:
        """Returns the model from cache, using `ForwardRef` if it's still being processed."""
        logger.debug(f"[DEBUG] Getting reference `{ref_name}`")

        if ref_name not in self._model_cache:
            raise ValueError(
                f"[ERROR] Reference `{ref_name}` not found in cache! Available: {list(self._model_cache.keys())}"
            )

        if self._model_cache[ref_name] is None:
            logger.debug(
                f"[WARNING] `{ref_name}` is still being processed. Using `ForwardRef('{ref_name}')` as a placeholder."
            )
            return ForwardRef(ref_name)

        return self._model_cache[ref_name]

    def _process_definitions(self, root_schema: Dict[str, Any]):
        """Preprocess all `$defs` models to ensure they are available before field processing."""
        if "$defs" in root_schema:
            for model_name, _ in root_schema["$defs"].items():
                if model_name not in self._model_cache:
                    logger.debug(f"[DEBUG] Pre-registering `{model_name}` to prevent recursion issues")
                    self._model_cache[model_name] = None  # Pre-register model to handle self-references

            for model_name, model_schema in root_schema["$defs"].items():
                if self._model_cache[model_name] is None:  # Only process if not fully created
                    logger.debug(f"[DEBUG] Processing `$defs` model `{model_name}`")
                    self._model_cache[model_name] = self.json_schema_to_pydantic(
                        model_schema, model_name, root_schema
                    )
                    logger.debug(f"[DEBUG] Completed `$defs` model `{model_name}`")

    def json_schema_to_pydantic(
        self, schema: Dict[str, Any], model_name: str = "GeneratedModel", root_schema: Dict[str, Any] = None
    ) -> Type[BaseModel]:
        """Converts JSON Schema into a Pydantic model."""
        logger.debug(f"[INFO] Processing schema `{model_name}`")

        if root_schema is None:
            root_schema = schema
            logger.debug("[DEBUG] Processing `$defs` before handling fields...")
            self._process_definitions(root_schema)

        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"], root_schema)

        return self.json_schema_to_pydantic_no_refs(schema, model_name, root_schema)

    def json_schema_to_pydantic_no_refs(
        self, schema: Dict[str, Any], model_name: str, root_schema: Dict[str, Any]
    ) -> Type[BaseModel]:
        """Processes schema **without resolving `$ref` dynamically**, ensuring all `$defs` are preprocessed first."""
        logger.debug(f"[DEBUG] Creating model `{model_name}`")

        fields = {}
        required_fields = set(schema.get("required", []))

        for key, value in schema.get("properties", {}).items():
            logger.debug(f"[DEBUG] Processing field `{key}` in `{model_name}`")

            json_type = value.get("type", None)
            field_type = TYPE_MAPPING.get(json_type)

            if json_type == "string" and "format" in value:
                if value["format"] not in FORMAT_MAPPING:
                    raise NotImplementedError(
                        f"[ERROR] Unknown format `{value['format']}` for `{key}` in `{model_name}`"
                    )
                field_type = FORMAT_MAPPING[value["format"]]

            if "$ref" in value:
                ref_name = value["$ref"].split("/")[-1]
                field_type = self.get_ref(ref_name)

            elif "anyOf" in value:
                sub_models = []
                for sub_schema in value["anyOf"]:
                    if "$ref" in sub_schema:
                        ref_name = sub_schema["$ref"].split("/")[-1]
                        sub_models.append(self.get_ref(ref_name))
                    else:
                        sub_models.append(TYPE_MAPPING.get(sub_schema.get("type", "string"), str))

                field_type = Union[tuple(sub_models)] if key in required_fields else Optional[Union[tuple(sub_models)]]

            elif json_type == "object" and "properties" in value:
                field_type = self.json_schema_to_pydantic_no_refs(value, f"{model_name}_{key}", root_schema)

            elif json_type == "array" and "items" in value:
                item_schema = value["items"]
                if "$ref" in item_schema:
                    ref_name = item_schema["$ref"].split("/")[-1]
                    item_type = self.get_ref(ref_name)
                else:
                    item_type = TYPE_MAPPING.get(item_schema.get("type", "string"), str)

                field_type = List[item_type]

            default_value = value.get("default", None)
            is_required = key in required_fields
            fields[key] = (field_type, Field(default=... if is_required else default_value))

        model = create_model(model_name, **fields)
        model.model_rebuild()

        logger.debug(f"[DEBUG] Completed model `{model_name}`")
        return model
