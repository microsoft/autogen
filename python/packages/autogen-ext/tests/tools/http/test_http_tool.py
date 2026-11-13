import json
import logging
from typing import Any, Literal

import httpx
import pytest
from autogen_core import CancellationToken, Component, ComponentModel
from autogen_ext.tools.http import HttpTool
from pydantic import ValidationError


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
async def test_post_request(test_config: ComponentModel, test_server: None, caplog: pytest.LogCaptureFixture) -> None:
    tool = HttpTool.load_component(test_config)

    with caplog.at_level(logging.INFO):
        result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

        assert isinstance(result, str)
        assert json.loads(result)["result"] == "Received: test query with value 42"

        assert "Received: test query with value 42" in caplog.text


@pytest.mark.asyncio
async def test_post_request_json_return(test_config: ComponentModel, test_server: None) -> None:
    # Modify config to use json return type
    config = test_config.model_copy()
    config.config["return_type"] = "json"
    tool = HttpTool.load_component(config)
    result = await tool.run_json({"query": "test query", "value": 45}, CancellationToken())

    assert isinstance(result, dict)
    assert result["result"] == "Received: test query with value 45"


@pytest.mark.asyncio
async def test_get_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for GET request
    config = test_config.model_copy()
    config.config["method"] = "GET"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_put_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for PUT request
    config = test_config.model_copy()
    config.config["method"] = "PUT"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_path_params(test_config: ComponentModel, test_server: None) -> None:
    # Modify config to use path parameters
    config = test_config.model_copy()
    config.config["path"] = "/test/{query}/{value}"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_path_params_and_body(test_config: ComponentModel, test_server: None) -> None:
    # Modify config to use path parameters and include body parameters
    config = test_config.model_copy()
    config.config["method"] = "PUT"
    config.config["path"] = "/test/{query}/{value}"
    config.config["json_schema"] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The test query"},
            "value": {"type": "integer", "description": "A test value"},
            "extra": {"type": "string", "description": "Extra body parameter"},
        },
        "required": ["query", "value", "extra"],
    }
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42, "extra": "extra data"}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42 and extra extra data"


@pytest.mark.asyncio
async def test_delete_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for DELETE request
    config = test_config.model_copy()
    config.config["method"] = "DELETE"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_patch_request(test_config: ComponentModel, test_server: None) -> None:
    # Modify config for PATCH request
    config = test_config.model_copy()
    config.config["method"] = "PATCH"
    tool = HttpTool.load_component(config)

    result = await tool.run_json({"query": "test query", "value": 42}, CancellationToken())

    assert isinstance(result, str)
    assert json.loads(result)["result"] == "Received: test query with value 42"


@pytest.mark.asyncio
async def test_invalid_schema(test_config: ComponentModel, test_server: None) -> None:
    # Create an invalid schema missing required properties
    config: ComponentModel = test_config.model_copy()
    config.config["host"] = True  # Incorrect type

    with pytest.raises(ValidationError):
        # Should fail when trying to create model from invalid schema
        HttpTool.load_component(config)


@pytest.mark.asyncio
async def test_invalid_request(test_config: ComponentModel, test_server: None) -> None:
    # Use an invalid URL
    config = test_config.model_copy()
    config.config["host"] = "fake"
    tool = HttpTool.load_component(config)

    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        await tool.run_json({"query": "test query", "value": 42}, CancellationToken())


def test_config_serialization(test_config: ComponentModel) -> None:
    tool = HttpTool.load_component(test_config)
    config = tool.dump_component()

    assert config.config["name"] == test_config.config["name"]
    assert config.config["description"] == test_config.config["description"]
    assert config.config["host"] == test_config.config["host"]
    assert config.config["port"] == test_config.config["port"]
    assert config.config["path"] == test_config.config["path"]
    assert config.config["scheme"] == test_config.config["scheme"]
    assert config.config["method"] == test_config.config["method"]
    assert config.config["headers"] == test_config.config["headers"]


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


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
@pytest.mark.parametrize(
    ("format_name", "value"),
    [
        ("date", "2026-10-15"),
        ("date-time", "2026-10-15T01:02:03Z"),
        ("uuid", "00000000-0000-4000-8000-000000000000"),
    ],
)
async def test_json_request_preserves_schema_formats(
    method: Literal["POST", "PUT", "PATCH"], format_name: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == method
        assert request.url.path == "/items/item-1"
        assert json.loads(request.content) == {"value": value, "active": True, "count": 3}
        return httpx.Response(200, json={"ok": True})

    original_client = httpx.AsyncClient

    def client_with_transport(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(handle_request), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_with_transport)
    tool = HttpTool(
        name="formatted_request",
        host="example.com",
        port=443,
        scheme="https",
        method=method,
        path="/items/{item}",
        return_type="json",
        json_schema={
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "value": {"type": "string", "format": format_name},
                "active": {"type": "boolean"},
                "count": {"type": "integer"},
            },
            "required": ["item", "value", "active", "count"],
        },
    )

    result = await tool.run_json({"item": "item-1", "value": value, "active": True, "count": 3}, CancellationToken())

    assert result == {"ok": True}
    assert len(requests) == 1
