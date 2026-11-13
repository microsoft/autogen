"""Shared test configuration and fixtures for component-schema-gen tests."""

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel


@pytest.fixture
def mock_config_schema():
    """Fixture providing a mock configuration schema."""
    class TestConfigSchema(BaseModel):
        api_key: str
        base_url: str = "https://api.example.com"
        timeout: int = 30

    return TestConfigSchema


@pytest.fixture
def mock_component_class(mock_config_schema):
    """Fixture providing a mock component class."""
    class MockComponentClass:
        component_config_schema = mock_config_schema
        component_type = "test_component"
        component_provider_override = None

        def __init__(self):
            pass

        @classmethod
        def __subclasshook__(cls, subclass):
            return True

    MockComponentClass.__name__ = "MockComponentClass"
    return MockComponentClass


@pytest.fixture
def mock_component_with_override(mock_config_schema):
    """Fixture providing a mock component class with provider override."""
    class MockComponentWithOverride:
        component_config_schema = mock_config_schema
        component_type = "override_component"
        component_provider_override = "custom_provider"

        @classmethod
        def __subclasshook__(cls, subclass):
            return True

    MockComponentWithOverride.__name__ = "MockComponentWithOverride"
    return MockComponentWithOverride


@pytest.fixture
def sample_json_schema() -> Dict[str, Any]:
    """Fixture providing a sample JSON schema structure."""
    return {
        "type": "object",
        "properties": {
            "config": {"$ref": "#/$defs/TestConfig"},
            "provider": {"type": "string", "const": "test_provider"},
            "component_type": {
                "anyOf": [
                    {"type": "string", "const": "test_component"},
                    {"type": "null"}
                ]
            }
        },
        "$defs": {
            "TestConfig": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "base_url": {"type": "string", "default": "https://api.example.com"},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["api_key"]
            }
        }
    }


@pytest.fixture
def mock_well_known_providers():
    """Fixture providing mock well-known providers mapping."""
    return {
        "openai": "openai_provider",
        "azure-openai": "azure_openai_provider",
        "azure-token": "azure_token_provider"
    }


@pytest.fixture
def mock_component_model_schema():
    """Fixture providing mock ComponentModel schema."""
    return {
        "type": "object",
        "properties": {
            "config": {},
            "provider": {},
            "component_type": {}
        },
        "$defs": {}
    }


@pytest.fixture(autouse=True)
def patch_imports(monkeypatch):
    """Auto-used fixture to patch problematic imports in test environment."""
    # Mock the ComponentToConfig base class check since it might not be available
    def mock_subclasscheck(cls, subclass):
        return True

    # You can add more patches here if needed for the test environment
    pass


class TestDataBuilder:
    """Helper class for building test data structures."""

    @staticmethod
    def create_mock_schema_with_defs(defs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock schema with specified definitions."""
        return {
            "type": "object",
            "properties": {},
            "$defs": defs
        }

    @staticmethod
    def create_component_schema(
        config_ref: str = "#/$defs/TestConfig",
        provider: str = "test_provider",
        component_type: str = "test_component"
    ) -> Dict[str, Any]:
        """Create a component schema with specified parameters."""
        return {
            "type": "object",
            "properties": {
                "config": {"$ref": config_ref},
                "provider": {"type": "string", "const": provider},
                "component_type": {
                    "anyOf": [
                        {"type": "string", "const": component_type},
                        {"type": "null"}
                    ]
                }
            },
            "$defs": {}
        }


# Test utilities that can be imported by test modules
def assert_valid_json_schema(schema: Dict[str, Any]) -> None:
    """Assert that a dictionary represents a valid JSON schema structure."""
    assert isinstance(schema, dict)
    assert "type" in schema

    if "properties" in schema:
        assert isinstance(schema["properties"], dict)

    if "$defs" in schema:
        assert isinstance(schema["$defs"], dict)


def assert_valid_component_schema(schema: Dict[str, Any]) -> None:
    """Assert that a dictionary represents a valid component schema."""
    assert_valid_json_schema(schema)

    # Component schemas should have these properties
    assert "properties" in schema
    properties = schema["properties"]

    assert "config" in properties
    assert "provider" in properties
    assert "component_type" in properties

    # Provider should be a constant string
    assert properties["provider"]["type"] == "string"
    assert "const" in properties["provider"]

    # Component type should allow string or null
    assert "anyOf" in properties["component_type"]
