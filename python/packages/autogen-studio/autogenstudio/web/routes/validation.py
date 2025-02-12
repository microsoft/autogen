# api/routes/validation.py
import importlib
from typing import Any, Dict, List, Optional

from autogen_core import ComponentModel, is_component_class
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ValidationRequest(BaseModel):
    component: Dict[str, Any]


class ValidationError(BaseModel):
    field: str
    error: str
    suggestion: Optional[str] = None


class ValidationResponse(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []


class ValidationService:
    @staticmethod
    def validate_provider(provider: str) -> Optional[ValidationError]:
        """Validate that the provider exists and can be imported"""
        try:
            if provider in ["azure_openai_chat_completion_client", "AzureOpenAIChatCompletionClient"]:
                provider = "autogen_ext.models.openai.AzureOpenAIChatCompletionClient"
            elif provider in ["openai_chat_completion_client", "OpenAIChatCompletionClient"]:
                provider = "autogen_ext.models.openai.OpenAIChatCompletionClient"

            module_path, class_name = provider.rsplit(".", maxsplit=1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)

            if not is_component_class(component_class):
                return ValidationError(
                    field="provider",
                    error=f"Class {provider} is not a valid component class",
                    suggestion="Ensure the class inherits from Component and implements required methods",
                )
            return None
        except ImportError:
            return ValidationError(
                field="provider",
                error=f"Could not import provider {provider}",
                suggestion="Check that the provider module is installed and the path is correct",
            )
        except Exception as e:
            return ValidationError(
                field="provider",
                error=f"Error validating provider: {str(e)}",
                suggestion="Check the provider string format and class implementation",
            )

    @staticmethod
    def validate_component_type(component: Dict[str, Any]) -> Optional[ValidationError]:
        """Validate the component type"""
        if "component_type" not in component:
            return ValidationError(
                field="component_type",
                error="Component type is missing",
                suggestion="Add a component_type field to the component configuration",
            )
        return None

    @staticmethod
    def validate_config_schema(component: Dict[str, Any]) -> List[ValidationError]:
        """Validate the component configuration against its schema"""
        errors = []
        try:
            # Convert to ComponentModel for initial validation
            model = ComponentModel(**component)

            # Get the component class
            provider = model.provider
            module_path, class_name = provider.rsplit(".", maxsplit=1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)

            # Validate against component's schema
            if hasattr(component_class, "component_config_schema"):
                try:
                    component_class.component_config_schema.model_validate(model.config)
                except Exception as e:
                    errors.append(
                        ValidationError(
                            field="config",
                            error=f"Config validation failed: {str(e)}",
                            suggestion="Check that the config matches the component's schema",
                        )
                    )
            else:
                errors.append(
                    ValidationError(
                        field="config",
                        error="Component class missing config schema",
                        suggestion="Implement component_config_schema in the component class",
                    )
                )
        except Exception as e:
            errors.append(
                ValidationError(
                    field="config",
                    error=f"Schema validation error: {str(e)}",
                    suggestion="Check the component configuration format",
                )
            )
        return errors

    @staticmethod
    def validate_instantiation(component: Dict[str, Any]) -> Optional[ValidationError]:
        """Validate that the component can be instantiated"""
        try:
            model = ComponentModel(**component)
            # Attempt to load the component
            module_path, class_name = model.provider.rsplit(".", maxsplit=1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)
            component_class.load_component(model)
            return None
        except Exception as e:
            return ValidationError(
                field="instantiation",
                error=f"Failed to instantiate component: {str(e)}",
                suggestion="Check that the component can be properly instantiated with the given config",
            )

    @classmethod
    def validate(cls, component: Dict[str, Any]) -> ValidationResponse:
        """Validate a component configuration"""
        errors = []
        warnings = []

        # Check provider
        if provider_error := cls.validate_provider(component.get("provider", "")):
            errors.append(provider_error)

        # Check component type
        if type_error := cls.validate_component_type(component):
            errors.append(type_error)

        # Validate schema
        schema_errors = cls.validate_config_schema(component)
        errors.extend(schema_errors)

        # Only attempt instantiation if no errors so far
        if not errors:
            if inst_error := cls.validate_instantiation(component):
                errors.append(inst_error)

        # Check for version warnings
        if "version" not in component:
            warnings.append(
                ValidationError(
                    field="version",
                    error="Component version not specified",
                    suggestion="Consider adding a version to ensure compatibility",
                )
            )

        return ValidationResponse(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


@router.post("/")
async def validate_component(request: ValidationRequest) -> ValidationResponse:
    """Validate a component configuration"""
    return ValidationService.validate(request.component)
