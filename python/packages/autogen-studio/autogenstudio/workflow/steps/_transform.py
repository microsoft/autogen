from typing import Any, Dict, Type, Optional
from pydantic import BaseModel, Field, ValidationError
from autogen_core import Component, ComponentBase
from ._step import BaseStep, BaseStepConfig
from ..core._models import StepMetadata, Context

class TransformStepConfig(BaseStepConfig):
    """Configuration for TransformStep serialization."""
    # mapping: {output_field: input_field or static value}
    mappings: Dict[str, Any] = Field(default_factory=dict, description="Field mappings from input to output")

class TransformStep(Component[TransformStepConfig], BaseStep[Any, Any]):
    """
    A generic, serializable step that maps fields from input to output schema.
    All logic is defined in config (mappings), so it is fully serializable and UI-friendly.
    """
    component_config_schema = TransformStepConfig
    component_type = "step"
    component_provider_override = "autogenstudio.workflow.steps.TransformStep"

    def __init__(
        self,
        step_id: str,
        metadata: StepMetadata,
        input_type: Type[BaseModel],
        output_type: Type[BaseModel],
        mappings: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(step_id, metadata, input_type, output_type)
        self.mappings = mappings or {}
        self._validate_mappings()

    def _validate_mappings(self):
        """
        Validate that all output fields are mapped to valid input fields or static values,
        and that types are compatible.
        Raises ValueError if invalid.
        """
        input_schema = self.input_type.model_json_schema()
        output_schema = self.output_type.model_json_schema()
        input_fields = input_schema.get("properties", {})
        output_fields = output_schema.get("properties", {})

        for out_field, in_field in self.mappings.items():
            if out_field not in output_fields:
                raise ValueError(f"Output field '{out_field}' not in output schema for step {self.step_id}")
            # If mapping is a string, treat as input field; else, static value
            if isinstance(in_field, str) and not in_field.startswith("static:"):
                if in_field not in input_fields:
                    raise ValueError(f"Input field '{in_field}' not in input schema for step {self.step_id}")
                # Optionally, check type compatibility (not strict for now)

    async def execute(self, input_data: BaseModel, context: Context) -> BaseModel:
        """
        Execute the transform: map fields from input to output according to config.
        """
        from ..schema_utils import coerce_value_to_schema_type
        
        output_kwargs = {}
        output_schema = self.output_type.model_json_schema()
        
        for out_field, in_field in self.mappings.items():
            # Get the raw value
            if isinstance(in_field, str):
                if in_field.startswith("static:"):
                    raw_value = in_field[len("static:"):]
                else:
                    raw_value = getattr(input_data, in_field, None)
            elif isinstance(in_field, dict):
                # Handle dict mappings with nested field resolution
                raw_value = {}
                for dict_key, dict_field in in_field.items():
                    if isinstance(dict_field, str):
                        if dict_field.startswith("static:"):
                            raw_value[dict_key] = dict_field[len("static:"):]
                        else:
                            raw_value[dict_key] = getattr(input_data, dict_field, None)
                    else:
                        raw_value[dict_key] = dict_field
            else:
                raw_value = in_field
            
            # Apply defensive type coercion using shared utility
            coerced_value = coerce_value_to_schema_type(raw_value, out_field, output_schema)
            output_kwargs[out_field] = coerced_value
            
        return self.output_type(**output_kwargs)

    def _to_config(self) -> TransformStepConfig:
        base_data = self._serialize_types()
        return TransformStepConfig(
            **base_data,
            mappings=self.mappings
        )

    @classmethod
    def _from_config(cls, config: TransformStepConfig) -> "TransformStep":
        input_type, output_type = cls._deserialize_types(config)
        return cls(
            step_id=config.step_id,
            metadata=config.metadata,
            input_type=input_type,
            output_type=output_type,
            mappings=config.mappings
        ) 