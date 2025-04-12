from contextlib import asynccontextmanager
import logging
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import (
    McpSessionActor,
    SseMcpToolAdapter,
    SseServerParams,
    StdioMcpToolAdapter,
    StdioServerParams,
    mcp_server_tools,
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
    # Create an instance of the adapter
    actor = McpSessionActor(server_params=sample_server_params)
    original_adapter = StdioMcpToolAdapter(actor=actor, tool=sample_tool)
    config = original_adapter.dump_component()
    loaded_adapter = StdioMcpToolAdapter.load_component(config)
    asyncio.run(actor.close())
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that adapter properly executes tools through ClientSession."""
    @asynccontextmanager
    async def fake_create_session(*args, **kwargs):  # type: ignore
        yield mock_session

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._session.create_mcp_server_session",
        fake_create_session,  # type: ignore
    )

    mock_session.call_tool.return_value = mock_tool_response

    with caplog.at_level(logging.INFO):
        actor = McpSessionActor(server_params=sample_server_params)
        await actor.initialize()
        adapter = StdioMcpToolAdapter(actor=actor, tool=sample_tool)
        result = await adapter.run_json(
            args=create_model(sample_tool.inputSchema)(**{"test_param": "test"}).model_dump(),
            cancellation_token=cancellation_token,
        )

        assert result == mock_tool_response.content
        mock_session.initialize.assert_called_once()
        mock_session.call_tool.assert_called_once()

        # Check log.
        assert "test_output" in caplog.text


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
    @asynccontextmanager
    async def fake_create_session(*args, **kwargs):  # type: ignore
        try:
            yield mock_session
        finally:
            # graceful shutdown
            pass

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._session.create_mcp_server_session",
        fake_create_session,  # type: ignore
    )

    mock_session.list_tools.return_value.tools = [sample_tool]

    adapter = await StdioMcpToolAdapter.from_server_params(sample_server_params, "test_tool")
    await adapter.close()
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
    actor = McpSessionActor(server_params=params)
    await actor.initialize()
    original_adapter = SseMcpToolAdapter(actor=actor, tool=sample_sse_tool)
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that SSE adapter properly executes tools through ClientSession."""
    params = SseServerParams(url="http://test-url")

    mock_result = MagicMock(isError=False, content={"result": "test_output"})
    mock_sse_session.call_tool.return_value = mock_result

    @asynccontextmanager
    async def fake_create_session(*args, **kwargs):  # type: ignore
        yield mock_sse_session

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._session.create_mcp_server_session",
        fake_create_session,  # type: ignore
    )

    with caplog.at_level(logging.INFO):
        actor = McpSessionActor(server_params=params)
        await actor.initialize()
        adapter = SseMcpToolAdapter(actor=actor, tool=sample_sse_tool)
        result = await adapter.run_json(
            args=create_model(sample_sse_tool.inputSchema)(**{"test_param": "test"}).model_dump(),
            cancellation_token=CancellationToken(),
        )

        assert result == mock_sse_session.call_tool.return_value.content
        mock_sse_session.initialize.assert_called_once()
        mock_sse_session.call_tool.assert_called_once()

        # Check log.
        assert "test_output" in caplog.text
        
        await actor.close()


@pytest.mark.asyncio
async def test_sse_adapter_from_server_params(
    sample_sse_tool: Tool,
    mock_sse_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that SSE adapter can be created from server parameters."""
    params = SseServerParams(url="http://test-url")
    mock_sse_session.list_tools.return_value.tools = [sample_sse_tool]

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_sse_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    @asynccontextmanager
    async def fake_create_session(*args, **kwargs):  # type: ignore
        yield mock_sse_session

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._session.create_mcp_server_session",
        fake_create_session,  # type: ignore
    )

    adapter = await SseMcpToolAdapter.from_server_params(params, "test_sse_tool")
    await adapter.close()

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


# TODO: why is this test not working in CI?
@pytest.mark.skip(reason="Skipping test_mcp_server_fetch due to CI issues.")
@pytest.mark.asyncio
async def test_mcp_server_fetch() -> None:
    params = StdioServerParams(
        command="uvx",
        args=["mcp-server-fetch"],
        read_timeout_seconds=60,
    )
    tools = await mcp_server_tools(server_params=params)
    assert tools is not None
    assert tools[0].name == "fetch"
    result = await tools[0].run_json({"url": "https://github.com/"}, CancellationToken())
    assert result is not None


# TODO: why is this test not working in CI?
@pytest.mark.skip(reason="Skipping due to CI issues.")
@pytest.mark.asyncio
async def test_mcp_server_filesystem() -> None:
    params = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            ".",
        ],
        read_timeout_seconds=60,
    )
    tools = await mcp_server_tools(server_params=params)
    assert tools is not None
    tools = [tool for tool in tools if tool.name == "read_file"]
    assert len(tools) == 1
    tool = tools[0]
    result = await tool.run_json({"path": "README.md"}, CancellationToken())
    assert result is not None


# TODO: why is this test not working in CI?
@pytest.mark.skip(reason="Skipping due to CI issues.")
@pytest.mark.asyncio
async def test_mcp_server_git() -> None:
    params = StdioServerParams(
        command="uvx",
        args=["mcp-server-git"],
        read_timeout_seconds=60,
    )
    tools = await mcp_server_tools(server_params=params)
    assert tools is not None
    tools = [tool for tool in tools if tool.name == "git_log"]
    assert len(tools) == 1
    tool = tools[0]
    repo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
    result = await tool.run_json({"repo_path": repo_path}, CancellationToken())
    assert result is not None


@pytest.mark.asyncio
async def test_mcp_server_github() -> None:
    # Check if GITHUB_TOKEN is set.
    if "GITHUB_TOKEN" not in os.environ:
        pytest.skip("GITHUB_TOKEN environment variable is not set. Skipping test.")
    params = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-github",
        ],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["GITHUB_TOKEN"]},
        read_timeout_seconds=60,
    )
    tools = await mcp_server_tools(server_params=params)
    assert tools is not None
    tools = [tool for tool in tools if tool.name == "get_file_contents"]
    assert len(tools) == 1
    tool = tools[0]
    result = await tool.run_json(
        {"owner": "microsoft", "repo": "autogen", "path": "python", "branch": "main"}, CancellationToken()
    )
    assert result is not None
