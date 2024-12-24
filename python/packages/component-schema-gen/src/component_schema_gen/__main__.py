import json
import sys
from typing import Any, DefaultDict, Dict, List, TypeVar

from autogen_core import ComponentModel
from autogen_core._component_config import (
    WELL_KNOWN_PROVIDERS,
    ComponentConfigImpl,
    _type_to_provider_str,  # type: ignore
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, AzureTokenProvider, OpenAIChatCompletionClient
from pydantic import BaseModel

all_defs: Dict[str, Any] = {}

T = TypeVar("T", bound=BaseModel)


def build_specific_component_schema(component: type[ComponentConfigImpl[T]], provider_str: str) -> Dict[str, Any]:
    model = component.component_config_schema  # type: ignore
    model_schema = model.model_json_schema()

    component_model_schema = ComponentModel.model_json_schema()
    if "$defs" not in component_model_schema:
        component_model_schema["$defs"] = {}

    if "$defs" not in model_schema:
        model_schema["$defs"] = {}
    component_model_schema["$defs"].update(model_schema["$defs"])  # type: ignore
    del model_schema["$defs"]

    if model.__name__ in component_model_schema["$defs"]:
        raise ValueError(f"Model {model.__name__} already exists in component")

    component_model_schema["$defs"][model.__name__] = model_schema

    component_model_schema["properties"]["config"] = {"$ref": f"#/$defs/{model.__name__}"}

    canonical_provider = component.component_provider_override or _type_to_provider_str(component)
    # TODO: generate this from the component and lookup table
    component_model_schema["properties"]["provider"] = {
        "anyOf": [
            {"type": "string", "const": canonical_provider},
        ]
    }

    component_model_schema["properties"]["provider"] = {"type": "string", "const": provider_str}

    component_model_schema["properties"]["component_type"] = {
        "anyOf": [{"type": "string", "const": component.component_type}, {"type": "null"}]
    }

    return component_model_schema


def main():
    outer_model_schema: Dict[str, Any] = {
        "type": "object",
        "$ref": "#/$defs/ComponentModel",
        "$defs": {
            "ComponentModel": {
                "type": "object",
                "oneOf": [],
            }
        },
    }

    reverse_provider_lookup_table: DefaultDict[str, List[str]] = DefaultDict(list)
    for key, value in WELL_KNOWN_PROVIDERS.items():
        reverse_provider_lookup_table[value].append(key)

    def add_type(type: type[ComponentConfigImpl[T]]):
        canonical = type.component_provider_override or _type_to_provider_str(type)
        reverse_provider_lookup_table[canonical].append(canonical)
        for provider_str in reverse_provider_lookup_table[canonical]:
            model = build_specific_component_schema(type, provider_str)
            # Add new defs, don't overwrite the existing ones
            for key, value in model["$defs"].items():
                if key in outer_model_schema["$defs"]:
                    print(f"Key {key} already exists in outer model schema", file=sys.stderr)
                    continue
                outer_model_schema["$defs"][key] = value
            del model["$defs"]
            outer_model_schema["$defs"][type.__name__ + "_prov:" + provider_str] = model

            outer_model_schema["$defs"]["ComponentModel"]["oneOf"].append(
                {"$ref": f"#/$defs/{type.__name__}_prov:{provider_str}"}
            )

    add_type(OpenAIChatCompletionClient)
    add_type(AzureOpenAIChatCompletionClient)
    add_type(AzureTokenProvider)

    print(json.dumps(outer_model_schema, indent=2))


if __name__ == "__main__":
    main()
