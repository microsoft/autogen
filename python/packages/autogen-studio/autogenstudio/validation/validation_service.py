# validation/validation_service.py
import importlib
from typing import List, Optional

from autogen_core import ComponentModel, is_component_class
from pydantic import BaseModel


class ValidationRequest(BaseModel):
    component: ComponentModel


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
    def validate_component_type(component: ComponentModel) -> Optional[ValidationError]:
        """Validate the component type"""
        if not component.component_type:
            return ValidationError(
                field="component_type",
                error="Component type is missing",
                suggestion="Add a component_type field to the component configuration",
            )

    @staticmethod
    def validate_config_schema(component: ComponentModel) -> List[ValidationError]:
        """Validate the component configuration against its schema"""
        errors: List[ValidationError] = []
        try:
            # Convert to ComponentModel for initial validation
            model = component.model_copy(deep=True)

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
    def validate_instantiation(component: ComponentModel) -> Optional[ValidationError]:
        """Validate that the component can be instantiated"""
        try:
            model = component.model_copy(deep=True)
            # Attempt to load the component
            module_path, class_name = model.provider.rsplit(".", maxsplit=1)
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)
            component_class.load_component(model)
            return None
        except Exception as e:
            error_str = str(e)
            
            # Check for version compatibility issues
            if "component_version" in error_str and "_from_config_past_version is not implemented" in error_str:
                # Extract component information for a better error message
                try:
                    # Get the current component version
                    module_path, class_name = component.provider.rsplit(".", maxsplit=1)
                    module = importlib.import_module(module_path)
                    component_class = getattr(module, class_name)
                    current_version = getattr(component_class, 'component_version', None)
                    config_version = component.component_version or component.version or 1
                    
                    return ValidationError(
                        field="component_version",
                        error=f"Component version mismatch: Your configuration uses version {config_version}, but the component requires version {current_version}",
                        suggestion=f"Update your component configuration to use version {current_version}. Set 'component_version: {current_version}' in your configuration.",
                    )
                except Exception:
                    # Fallback to a more general version error message
                    return ValidationError(
                        field="component_version",
                        error="Component version compatibility issue detected",
                        suggestion="Your component configuration version is outdated. Update the 'component_version' field to match the latest component requirements.",
                    )
            
            # Check for other common instantiation issues
            elif "Could not import provider" in error_str or "ImportError" in error_str:
                return ValidationError(
                    field="provider",
                    error=f"Provider import failed: {error_str}",
                    suggestion="Ensure the provider module is installed and the import path is correct",
                )
            elif "component_config_schema" in error_str:
                return ValidationError(
                    field="config",
                    error="Component configuration schema validation failed",
                    suggestion="Check that your configuration matches the component's expected schema",
                )
            else:
                return ValidationError(
                    field="instantiation",
                    error=f"Failed to instantiate component: {error_str}",
                    suggestion="Check that the component can be properly instantiated with the given config",
                )

    @classmethod
    def validate(cls, component: ComponentModel) -> ValidationResponse:
        """Validate a component configuration"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Check provider
        if provider_error := cls.validate_provider(component.provider):
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
        if not component.version:
            warnings.append(
                ValidationError(
                    field="version",
                    error="Component version not specified",
                    suggestion="Consider adding a version to ensure compatibility",
                )
            )

        return ValidationResponse(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
