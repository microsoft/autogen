import pytest
import httpx
from pydantic import ValidationError
from autogen_core import CancellationToken
from autogen_ext.tools.http import HttpTool
from autogen_core import Component, ComponentModel


def test_tool_schema_generation(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)
    schema = tool.schema

    assert schema["name"] == "TestHttpTool"
    assert "description" in schema
    assert schema["description"] == "A test HTTP tool"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "properties" in schema["parameters"]
    assert schema["parameters"]["properties"]["query"]["description"] == "The test query"
    assert schema["parameters"]["properties"]["query"]["type"] == "string"
    assert schema["parameters"]["properties"]["value"]["description"] == "A test value"
    assert schema["parameters"]["properties"]["value"]["type"] == "integer"
    assert "required" in schema["parameters"]
    assert set(schema["parameters"]["required"]) == {"query", "value"}


def test_tool_properties(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)

    assert tool.name == "TestHttpTool"
    assert tool.description == "A test HTTP tool"
    assert tool.server_params.host == "localhost"
    assert tool.server_params.port == 8000
    assert tool.server_params.path == "/test"
    assert tool.server_params.scheme == "http"
    assert tool.server_params.method == "POST"


def test_component_base_class(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)
    assert tool.dump_component() is not None
    assert HttpTool.load_component(tool.dump_component(), HttpTool) is not None
    assert isinstance(tool, Component)


@pytest.mark.asyncio
async def test_post_request(test_config: ComponentModel, test_server: None) -> None:
    tool = HttpTool.load_component(test_config)
    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_get_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for GET request
    config = test_config.model_copy()
    config.config["method"] = "GET"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_put_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for PUT request
    config = test_config.model_copy()
    config.config["method"] = "PUT"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_delete_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for DELETE request
    config = test_config.model_copy()
    config.config["method"] = "DELETE"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_patch_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for PATCH request
    config = test_config.model_copy()
    config.config["method"] = "PATCH"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_invalid_schema(test_config: ComponentModel, test_server: None) -> None:
    # Create an invalid schema missing required properties
    config: ComponentModel = test_config.model_copy()
    config.config["host"] = True # Incorrect type

    with pytest.raises(ValidationError):
        # Should fail when trying to create model from invalid schema
        HttpTool.load_component(config)


@pytest.mark.asyncio
async def test_invalid_request(test_config: ComponentModel, test_server: None) -> None:
    # Use an invalid URL
    config = test_config.model_copy()
    config.config["host"] = "fake"
    tool = HttpTool.load_component(config)

    with pytest.raises(httpx.ConnectError):
        await tool.run_json({"query": "test query", "value": 42}, CancellationToken())


def test_config_serialization(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)
    config = tool._to_config()

    assert config.name == test_config.config["name"]
    assert config.description == test_config.config["description"]
    assert config.host == test_config.config["host"]
    assert config.port == test_config.config["port"]
    assert config.path == test_config.config["path"]
    assert config.scheme == test_config.config["scheme"]
    assert config.method == test_config.config["method"]
    assert config.headers == test_config.config["headers"]


def test_config_deserialization(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)

    assert tool.name == test_config.config["name"]
    assert tool.description == test_config.config["description"]
    assert tool.server_params.host == test_config.config["host"]
    assert tool.server_params.port == test_config.config["port"]
    assert tool.server_params.path == test_config.config["path"]
    assert tool.server_params.scheme == test_config.config["scheme"]
    assert tool.server_params.method == test_config.config["method"]
    assert tool.server_params.headers == test_config.config["headers"]
