import logging
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_core.tools import Workbench
from autogen_core.utils import schema_to_pydantic_model
from autogen_ext.tools.mcp import (
    McpWorkbench,
    SseMcpToolAdapter,
    SseServerParams,
    StdioMcpToolAdapter,
    StdioServerParams,
    create_mcp_server_session,
    mcp_server_tools,
)
from mcp import ClientSession, Tool
from mcp.types import (
    Annotations,
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from pydantic.networks import AnyUrl


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
    response.content = [
        TextContent(
            text="test_output",
            type="text",
            annotations=Annotations(audience=["user", "assistant"], priority=0.7),
        ),
    ]
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that adapter properly executes tools through ClientSession."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    mock_session.call_tool.return_value = mock_tool_response

    with caplog.at_level(logging.INFO):
        adapter = StdioMcpToolAdapter(server_params=sample_server_params, tool=sample_tool)
        result = await adapter.run_json(
            args=schema_to_pydantic_model(sample_tool.inputSchema)(**{"test_param": "test"}).model_dump(),
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
async def test_adapter_from_server_params_with_return_value_as_string(
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

    assert (
        adapter.return_value_as_string(
            [
                TextContent(
                    text="this is a sample text",
                    type="text",
                    annotations=Annotations(audience=["user", "assistant"], priority=0.7),
                ),
                ImageContent(
                    data="this is a sample base64 encoded image",
                    mimeType="image/png",
                    type="image",
                    annotations=None,
                ),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(
                        text="this is a sample text",
                        uri=AnyUrl(url="http://example.com/test"),
                    ),
                    annotations=Annotations(audience=["user"], priority=0.3),
                ),
            ]
        )
        == '[{"type": "text", "text": "this is a sample text", "annotations": {"audience": ["user", "assistant"], "priority": 0.7}}, {"type": "image", "data": "this is a sample base64 encoded image", "mimeType": "image/png", "annotations": null}, {"type": "resource", "resource": {"uri": "http://example.com/test", "mimeType": null, "text": "this is a sample text"}, "annotations": {"audience": ["user"], "priority": 0.3}}]'
    )


@pytest.mark.asyncio
async def test_adapter_from_factory(
    sample_tool: Tool,
    sample_server_params: StdioServerParams,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that factory function returns a list of tools."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._factory.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )
    mock_session.list_tools.return_value.tools = [sample_tool]
    tools = await mcp_server_tools(server_params=sample_server_params)
    assert tools is not None
    assert len(tools) > 0
    assert isinstance(tools[0], StdioMcpToolAdapter)


@pytest.mark.asyncio
async def test_adapter_from_factory_existing_session(
    sample_tool: Tool,
    sample_server_params: StdioServerParams,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that factory function returns a list of tools with an existing session."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    monkeypatch.setattr(
        "autogen_ext.tools.mcp._factory.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )
    mock_session.list_tools.return_value.tools = [sample_tool]
    tools = await mcp_server_tools(server_params=sample_server_params, session=mock_session)
    assert tools is not None
    assert len(tools) > 0
    assert isinstance(tools[0], StdioMcpToolAdapter)


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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that SSE adapter properly executes tools through ClientSession."""
    params = SseServerParams(url="http://test-url")
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_sse_session

    mock_sse_session.call_tool.return_value = MagicMock(isError=False, content=[
        TextContent(
            text="test_output",
            type="text",
            annotations=Annotations(audience=["user", "assistant"], priority=0.7),
        ),
    ])

    monkeypatch.setattr(
        "autogen_ext.tools.mcp._base.create_mcp_server_session",
        lambda *args, **kwargs: mock_context,  # type: ignore
    )

    with caplog.at_level(logging.INFO):
        adapter = SseMcpToolAdapter(server_params=params, tool=sample_sse_tool)
        result = await adapter.run_json(
            args=schema_to_pydantic_model(sample_sse_tool.inputSchema)(**{"test_param": "test"}).model_dump(),
            cancellation_token=CancellationToken(),
        )

        assert result == mock_sse_session.call_tool.return_value.content
        mock_sse_session.initialize.assert_called_once()
        mock_sse_session.call_tool.assert_called_once()

        # Check log.
        assert "test_output" in caplog.text


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
async def test_mcp_server_git_existing_session() -> None:
    params = StdioServerParams(
        command="uvx",
        args=["mcp-server-git"],
        read_timeout_seconds=60,
    )
    async with create_mcp_server_session(params) as session:
        await session.initialize()
        tools = await mcp_server_tools(server_params=params, session=session)
        assert tools is not None
        git_log = [tool for tool in tools if tool.name == "git_log"][0]
        repo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
        result = await git_log.run_json({"repo_path": repo_path}, CancellationToken())
        assert result is not None

        git_status = [tool for tool in tools if tool.name == "git_status"][0]
        result = await git_status.run_json({"repo_path": repo_path}, CancellationToken())
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
        {"owner": "microsoft", "repo": "autogen", "path": "python", "branch": "main"},
        CancellationToken(),
    )
    assert result is not None


@pytest.mark.asyncio
async def test_mcp_workbench_start_stop() -> None:
    params = StdioServerParams(
        command="uvx",
        args=["mcp-server-fetch"],
        read_timeout_seconds=60,
    )

    workbench = McpWorkbench(params)
    assert workbench is not None
    assert workbench.server_params == params
    await workbench.start()
    assert workbench._actor is not None  # type: ignore[reportPrivateUsage]
    await workbench.stop()
    assert workbench._actor is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_mcp_workbench_server_fetch() -> None:
    params = StdioServerParams(
        command="uvx",
        args=["mcp-server-fetch"],
        read_timeout_seconds=60,
    )

    workbench = McpWorkbench(server_params=params)
    await workbench.start()

    tools = await workbench.list_tools()
    assert tools is not None
    assert tools[0]["name"] == "fetch"

    result = await workbench.call_tool(tools[0]["name"], {"url": "https://github.com/"}, CancellationToken())
    assert result is not None

    await workbench.stop()


@pytest.mark.asyncio
async def test_mcp_workbench_server_filesystem() -> None:
    params = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            ".",
        ],
        read_timeout_seconds=60,
    )

    workbench = McpWorkbench(server_params=params)
    await workbench.start()

    tools = await workbench.list_tools()
    assert tools is not None
    tools = [tool for tool in tools if tool["name"] == "read_file"]
    assert len(tools) == 1
    tool = tools[0]
    result = await workbench.call_tool(tool["name"], {"path": "README.md"}, CancellationToken())
    assert result is not None

    await workbench.stop()

    # Serialize the workbench.
    config = workbench.dump_component()

    # Deserialize the workbench.
    async with Workbench.load_component(config) as new_workbench:
        tools = await new_workbench.list_tools()
        assert tools is not None
        tools = [tool for tool in tools if tool["name"] == "read_file"]
        assert len(tools) == 1
        tool = tools[0]
        result = await new_workbench.call_tool(tool["name"], {"path": "README.md"}, CancellationToken())
        assert result is not None
