from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import (
    SseMcpToolAdapter,
    SseServerParams,
    StdioMcpToolAdapter,
    StdioServerParams,
)
from json_schema_to_pydantic import create_model
from mcp import ClientSession, Tool


@pytest.fixture
def sample_tool() -> Tool:
    return Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={
            "type": "object",
            "properties": {"test_param": {"type": "string"}},
            "required": ["test_param"],
        },
    )


@pytest.fixture
def sample_server_params() -> StdioServerParams:
    return StdioServerParams(command="echo", args=["test"])


@pytest.fixture
def sample_sse_tool() -> Tool:
    return Tool(
        name="test_sse_tool",
        description="A test SSE tool",
        inputSchema={
            "type": "object",
            "properties": {"test_param": {"type": "string"}},
            "required": ["test_param"],
        },
    )


@pytest.fixture
def mock_sse_session() -> AsyncMock:
    session = AsyncMock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock()
    session.list_tools = AsyncMock()
    return session


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock()
    session.list_tools = AsyncMock()
    return session


@pytest.fixture
def mock_tool_response() -> MagicMock:
    response = MagicMock()
    response.isError = False
    response.content = {"result": "test_output"}
    return response


@pytest.fixture
def cancellation_token() -> CancellationToken:
    return CancellationToken()


def test_adapter_config_serialization(sample_tool: Tool, sample_server_params: StdioServerParams) -> None:
    """Test that adapter can be saved to and loaded from config."""
    original_adapter = StdioMcpToolAdapter(server_params=sample_server_params, tool=sample_tool)
    config = original_adapter.dump_component()
    loaded_adapter = StdioMcpToolAdapter.load_component(config)

    # Test that the loaded adapter has the same properties
    assert loaded_adapter.name == "test_tool"
    assert loaded_adapter.description == "A test tool"

    # Verify schema structure
    schema = loaded_adapter.schema
    assert "parameters" in schema, "Schema must have parameters"
    params_schema = schema["parameters"]
    assert isinstance(params_schema, dict), "Parameters must be a dict"
    assert "type" in params_schema, "Parameters must have type"
    assert "required" in params_schema, "Parameters must have required fields"
    assert "properties" in params_schema, "Parameters must have properties"

    # Compare schema content
    assert params_schema["type"] == sample_tool.inputSchema["type"]
    assert params_schema["required"] == sample_tool.inputSchema["required"]
    assert (
        params_schema["properties"]["test_param"]["type"] == sample_tool.inputSchema["properties"]["test_param"]["type"]
    )


@pytest.mark.asyncio
async def test_mcp_tool_execution(
    sample_tool: Tool,
    sample_server_params: StdioServerParams,
    mock_session: AsyncMock,
    mock_tool_response: MagicMock,
    cancellation_token: CancellationToken,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that adapter properly executes tools through ClientSession."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    mock_session.call_tool.return_value = mock_tool_response

    adapter = StdioMcpToolAdapter(server_params=sample_server_params, tool=sample_tool)
    result = await adapter.run(
        args=create_model(sample_tool.inputSchema)(**{"test_param": "test"}),
        cancellation_token=cancellation_token,
    )

    assert result == mock_tool_response.content
    mock_session.initialize.assert_called_once()
    mock_session.call_tool.assert_called_once()


@pytest.mark.asyncio
async def test_adapter_from_server_params(
    sample_tool: Tool,
    sample_server_params: StdioServerParams,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that adapter can be created from server parameters."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    mock_session.list_tools.return_value.tools = [sample_tool]

    adapter = await StdioMcpToolAdapter.from_server_params(sample_server_params, "test_tool")

    assert isinstance(adapter, StdioMcpToolAdapter)
    assert adapter.name == "test_tool"
    assert adapter.description == "A test tool"

    # Verify schema structure
    schema = adapter.schema
    assert "parameters" in schema, "Schema must have parameters"
    params_schema = schema["parameters"]
    assert isinstance(params_schema, dict), "Parameters must be a dict"
    assert "type" in params_schema, "Parameters must have type"
    assert "required" in params_schema, "Parameters must have required fields"
    assert "properties" in params_schema, "Parameters must have properties"

    # Compare schema content
    assert params_schema["type"] == sample_tool.inputSchema["type"]
    assert params_schema["required"] == sample_tool.inputSchema["required"]
    assert (
        params_schema["properties"]["test_param"]["type"] == sample_tool.inputSchema["properties"]["test_param"]["type"]
    )


@pytest.mark.asyncio
async def test_sse_adapter_config_serialization(sample_sse_tool: Tool) -> None:
    """Test that SSE adapter can be saved to and loaded from config."""
    params = SseServerParams(url="http://test-url")
    original_adapter = SseMcpToolAdapter(server_params=params, tool=sample_sse_tool)
    config = original_adapter.dump_component()
    loaded_adapter = SseMcpToolAdapter.load_component(config)

    # Test that the loaded adapter has the same properties
    assert loaded_adapter.name == "test_sse_tool"
    assert loaded_adapter.description == "A test SSE tool"

    # Verify schema structure
    schema = loaded_adapter.schema
    assert "parameters" in schema, "Schema must have parameters"
    params_schema = schema["parameters"]
    assert isinstance(params_schema, dict), "Parameters must be a dict"
    assert "type" in params_schema, "Parameters must have type"
    assert "required" in params_schema, "Parameters must have required fields"
    assert "properties" in params_schema, "Parameters must have properties"

    # Compare schema content
    assert params_schema["type"] == sample_sse_tool.inputSchema["type"]
    assert params_schema["required"] == sample_sse_tool.inputSchema["required"]
    assert (
        params_schema["properties"]["test_param"]["type"]
        == sample_sse_tool.inputSchema["properties"]["test_param"]["type"]
    )


@pytest.mark.asyncio
async def test_sse_tool_execution(
    sample_sse_tool: Tool,
    mock_sse_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that SSE adapter properly executes tools through ClientSession."""
    params = SseServerParams(url="http://test-url")
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_sse_session

    mock_sse_session.call_tool.return_value = MagicMock(isError=False, content={"result": "test_output"})

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    adapter = SseMcpToolAdapter(server_params=params, tool=sample_sse_tool)
    result = await adapter.run(
        args=create_model(sample_sse_tool.inputSchema)(**{"test_param": "test"}),
        cancellation_token=CancellationToken(),
    )

    assert result == mock_sse_session.call_tool.return_value.content
    mock_sse_session.initialize.assert_called_once()
    mock_sse_session.call_tool.assert_called_once()


@pytest.mark.asyncio
async def test_sse_adapter_from_server_params(
    sample_sse_tool: Tool,
    mock_sse_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that SSE adapter can be created from server parameters."""
    params = SseServerParams(url="http://test-url")
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_sse_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    mock_sse_session.list_tools.return_value.tools = [sample_sse_tool]

    adapter = await SseMcpToolAdapter.from_server_params(params, "test_sse_tool")

    assert isinstance(adapter, SseMcpToolAdapter)
    assert adapter.name == "test_sse_tool"
    assert adapter.description == "A test SSE tool"

    # Verify schema structure
    schema = adapter.schema
    assert "parameters" in schema, "Schema must have parameters"
    params_schema = schema["parameters"]
    assert isinstance(params_schema, dict), "Parameters must be a dict"
    assert "type" in params_schema, "Parameters must have type"
    assert "required" in params_schema, "Parameters must have required fields"
    assert "properties" in params_schema, "Parameters must have properties"

    # Compare schema content
    assert params_schema["type"] == sample_sse_tool.inputSchema["type"]
    assert params_schema["required"] == sample_sse_tool.inputSchema["required"]
    assert (
        params_schema["properties"]["test_param"]["type"]
        == sample_sse_tool.inputSchema["properties"]["test_param"]["type"]
    )
