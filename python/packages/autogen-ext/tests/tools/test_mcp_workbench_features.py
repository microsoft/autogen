import asyncio
from unittest.mock import AsyncMock

import pytest
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from mcp.types import (
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
)
from pydantic import AnyUrl


@pytest.fixture
def sample_server_params() -> StdioServerParams:
    """Sample server parameters for testing."""
    return StdioServerParams(command="echo", args=["test"])


@pytest.fixture
def mock_mcp_actor() -> AsyncMock:
    """Mock MCP session actor."""
    actor = AsyncMock()
    return actor


@pytest.fixture
def sample_prompts() -> list[Prompt]:
    """Create sample MCP prompts for testing."""
    return [
        Prompt(
            name="code_review",
            description="Reviews code for best practices",
            arguments=[
                PromptArgument(
                    name="language",
                    description="Programming language",
                    required=True,
                )
            ],
        ),
        Prompt(
            name="documentation",
            description="Generates documentation",
            arguments=[
                PromptArgument(
                    name="format",
                    description="Output format",
                    required=False,
                )
            ],
        ),
    ]


@pytest.fixture
def sample_resources() -> list[Resource]:
    """Create sample MCP resources for testing."""
    return [
        Resource(
            uri=AnyUrl("file:///test/document.txt"),
            name="Test Document",
            description="A sample document for testing",
            mimeType="text/plain",
        ),
        Resource(
            uri=AnyUrl("https://api.example.com/data"),
            name="API Data",
            description="External API data source",
            mimeType="application/json",
        ),
    ]


@pytest.fixture
def sample_resource_templates() -> list[ResourceTemplate]:
    """Create sample MCP resource templates for testing."""
    return [
        ResourceTemplate(
            uriTemplate="file:///logs/{date}.log",
            name="Daily Logs",
            description="Daily log files by date",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="https://api.example.com/users/{userId}",
            name="User Profile",
            description="User profile by ID",
            mimeType="application/json",
        ),
    ]


@pytest.mark.asyncio
async def test_list_prompts(
    sample_prompts: list[Prompt], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
) -> None:
    """Test listing prompts from MCP server."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock list_prompts response
    list_prompts_result = ListPromptsResult(prompts=sample_prompts)
    future_result: asyncio.Future[ListPromptsResult] = asyncio.Future()
    future_result.set_result(list_prompts_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # List prompts
        result = await workbench.list_prompts()

        # Verify result
        assert isinstance(result, ListPromptsResult)
        assert len(result.prompts) == 2
        assert result.prompts[0].name == "code_review"
        assert result.prompts[0].description == "Reviews code for best practices"
        assert result.prompts[1].name == "documentation"
        assert result.prompts[1].description == "Generates documentation"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_prompts", None)

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_get_prompt_without_arguments(mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams) -> None:
    """Test getting a prompt without arguments."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock get_prompt response
    get_prompt_result = GetPromptResult(
        description="Code review prompt",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text="Please review this code for best practices and suggest improvements.",
                ),
            )
        ],
    )
    future_result: asyncio.Future[GetPromptResult] = asyncio.Future()
    future_result.set_result(get_prompt_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Get prompt
        result = await workbench.get_prompt("code_review")

        # Verify result
        assert isinstance(result, GetPromptResult)
        assert result.description == "Code review prompt"
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("get_prompt", {"name": "code_review", "kargs": {"arguments": None}})

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_get_prompt_with_arguments(mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams) -> None:
    """Test getting a prompt with arguments."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock get_prompt response
    get_prompt_result = GetPromptResult(
        description="Python code review prompt",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text="Please review this Python code for best practices and suggest improvements.",
                ),
            )
        ],
    )
    future_result: asyncio.Future[GetPromptResult] = asyncio.Future()
    future_result.set_result(get_prompt_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Get prompt with arguments
        arguments = {"language": "python", "style": "pep8"}
        result = await workbench.get_prompt("code_review", arguments)

        # Verify result
        assert isinstance(result, GetPromptResult)
        assert result.description == "Python code review prompt"
        assert len(result.messages) == 1

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("get_prompt", {"name": "code_review", "kargs": {"arguments": arguments}})

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_list_resources(
    sample_resources: list[Resource], mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams
) -> None:
    """Test listing resources from MCP server."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock list_resources response
    list_resources_result = ListResourcesResult(resources=sample_resources)
    future_result: asyncio.Future[ListResourcesResult] = asyncio.Future()
    future_result.set_result(list_resources_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # List resources
        result = await workbench.list_resources()

        # Verify result
        assert isinstance(result, ListResourcesResult)
        assert len(result.resources) == 2
        assert str(result.resources[0].uri) == "file:///test/document.txt"
        assert result.resources[0].name == "Test Document"
        assert result.resources[0].mimeType == "text/plain"
        assert str(result.resources[1].uri) == "https://api.example.com/data"
        assert result.resources[1].name == "API Data"
        assert result.resources[1].mimeType == "application/json"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_resources", None)

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_read_resource(mock_mcp_actor: AsyncMock, sample_server_params: StdioServerParams) -> None:
    """Test reading a resource from MCP server."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock read_resource response
    read_resource_result = ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=AnyUrl("file:///test/document.txt"),
                mimeType="text/plain",
                text="This is the content of the test document.",
            )
        ]
    )
    future_result: asyncio.Future[ReadResourceResult] = asyncio.Future()
    future_result.set_result(read_resource_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Read resource
        uri = "file:///test/document.txt"
        result = await workbench.read_resource(uri)

        # Verify result
        assert isinstance(result, ReadResourceResult)
        assert len(result.contents) == 1
        content = result.contents[0]
        assert isinstance(content, TextResourceContents)
        assert content.uri == AnyUrl(uri)
        assert content.mimeType == "text/plain"
        assert content.text == "This is the content of the test document."

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("read_resource", {"name": None, "kargs": {"uri": uri}})

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_list_resource_templates(
    sample_resource_templates: list[ResourceTemplate],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
) -> None:
    """Test listing resource templates from MCP server."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)
    workbench._actor = mock_mcp_actor  # type: ignore[reportPrivateUsage]

    # Mock list_resource_templates response
    list_templates_result = ListResourceTemplatesResult(resourceTemplates=sample_resource_templates)
    future_result: asyncio.Future[ListResourceTemplatesResult] = asyncio.Future()
    future_result.set_result(list_templates_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # List resource templates
        result = await workbench.list_resource_templates()

        # Verify result
        assert isinstance(result, ListResourceTemplatesResult)
        assert len(result.resourceTemplates) == 2
        assert result.resourceTemplates[0].uriTemplate == "file:///logs/{date}.log"
        assert result.resourceTemplates[0].name == "Daily Logs"
        assert result.resourceTemplates[0].mimeType == "text/plain"
        assert result.resourceTemplates[1].uriTemplate == "https://api.example.com/users/{userId}"
        assert result.resourceTemplates[1].name == "User Profile"
        assert result.resourceTemplates[1].mimeType == "application/json"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_resource_templates", None)

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_workbench_auto_start_on_list_prompts(
    sample_prompts: list[Prompt], sample_server_params: StdioServerParams
) -> None:
    """Test that workbench automatically starts when list_prompts is called without explicit start."""
    # Create workbench without starting it
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock the start method to avoid actual server connection
    original_start = workbench.start
    start_called = False

    async def mock_start() -> None:
        nonlocal start_called
        start_called = True
        # Set up a mock actor
        mock_actor = AsyncMock()
        list_prompts_result = ListPromptsResult(prompts=sample_prompts)
        future_result: asyncio.Future[ListPromptsResult] = asyncio.Future()
        future_result.set_result(list_prompts_result)
        mock_actor.call.return_value = future_result
        workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    try:
        # Call list_prompts without explicitly starting
        result = await workbench.list_prompts()

        # Verify that start was called
        assert start_called
        assert isinstance(result, ListPromptsResult)
        assert len(result.prompts) == 2

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]
        workbench.start = original_start  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_workbench_auto_start_on_get_prompt(sample_server_params: StdioServerParams) -> None:
    """Test that workbench automatically starts when get_prompt is called without explicit start."""
    # Create workbench without starting it
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock the start method to avoid actual server connection
    start_called = False

    async def mock_start() -> None:
        nonlocal start_called
        start_called = True
        # Set up a mock actor
        mock_actor = AsyncMock()
        get_prompt_result = GetPromptResult(
            description="Test prompt",
            messages=[PromptMessage(role="user", content=TextContent(type="text", text="Test message"))],
        )
        future_result: asyncio.Future[GetPromptResult] = asyncio.Future()
        future_result.set_result(get_prompt_result)
        mock_actor.call.return_value = future_result
        workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    try:
        # Call get_prompt without explicitly starting
        result = await workbench.get_prompt("test_prompt")

        # Verify that start was called
        assert start_called
        assert isinstance(result, GetPromptResult)
        assert result.description == "Test prompt"

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_workbench_auto_start_on_list_resources(
    sample_resources: list[Resource], sample_server_params: StdioServerParams
) -> None:
    """Test that workbench automatically starts when list_resources is called without explicit start."""
    # Create workbench without starting it
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock the start method to avoid actual server connection
    start_called = False

    async def mock_start() -> None:
        nonlocal start_called
        start_called = True
        # Set up a mock actor
        mock_actor = AsyncMock()
        list_resources_result = ListResourcesResult(resources=sample_resources)
        future_result: asyncio.Future[ListResourcesResult] = asyncio.Future()
        future_result.set_result(list_resources_result)
        mock_actor.call.return_value = future_result
        workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    try:
        # Call list_resources without explicitly starting
        result = await workbench.list_resources()

        # Verify that start was called
        assert start_called
        assert isinstance(result, ListResourcesResult)
        assert len(result.resources) == 2

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_workbench_auto_start_on_read_resource(sample_server_params: StdioServerParams) -> None:
    """Test that workbench automatically starts when read_resource is called without explicit start."""
    # Create workbench without starting it
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock the start method to avoid actual server connection
    start_called = False

    async def mock_start() -> None:
        nonlocal start_called
        start_called = True
        # Set up a mock actor
        mock_actor = AsyncMock()
        read_resource_result = ReadResourceResult(
            contents=[TextResourceContents(uri=AnyUrl("file:///test.txt"), mimeType="text/plain", text="Test content")]
        )
        future_result: asyncio.Future[ReadResourceResult] = asyncio.Future()
        future_result.set_result(read_resource_result)
        mock_actor.call.return_value = future_result
        workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    try:
        # Call read_resource without explicitly starting
        result = await workbench.read_resource("file:///test.txt")

        # Verify that start was called
        assert start_called
        assert isinstance(result, ReadResourceResult)
        assert len(result.contents) == 1

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_workbench_auto_start_on_list_resource_templates(
    sample_resource_templates: list[ResourceTemplate], sample_server_params: StdioServerParams
) -> None:
    """Test that workbench automatically starts when list_resource_templates is called without explicit start."""
    # Create workbench without starting it
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock the start method to avoid actual server connection
    start_called = False

    async def mock_start() -> None:
        nonlocal start_called
        start_called = True
        # Set up a mock actor
        mock_actor = AsyncMock()
        list_templates_result = ListResourceTemplatesResult(resourceTemplates=sample_resource_templates)
        future_result: asyncio.Future[ListResourceTemplatesResult] = asyncio.Future()
        future_result.set_result(list_templates_result)
        mock_actor.call.return_value = future_result
        workbench._actor = mock_actor  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    try:
        # Call list_resource_templates without explicitly starting
        result = await workbench.list_resource_templates()

        # Verify that start was called
        assert start_called
        assert isinstance(result, ListResourceTemplatesResult)
        assert len(result.resourceTemplates) == 2

    finally:
        workbench._actor = None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_workbench_methods_raise_error_if_actor_fails_to_initialize(
    sample_server_params: StdioServerParams,
) -> None:
    """Test that methods raise RuntimeError if actor fails to initialize."""
    # Create workbench
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock start to set actor to None (simulating initialization failure)
    async def mock_start() -> None:
        workbench._actor = None  # type: ignore[reportPrivateUsage]

    workbench.start = mock_start  # type: ignore[method-assign]

    # Test that all methods raise RuntimeError when actor is None
    with pytest.raises(RuntimeError, match="Actor is not initialized"):
        await workbench.list_prompts()

    with pytest.raises(RuntimeError, match="Actor is not initialized"):
        await workbench.get_prompt("test")

    with pytest.raises(RuntimeError, match="Actor is not initialized"):
        await workbench.list_resources()

    with pytest.raises(RuntimeError, match="Actor is not initialized"):
        await workbench.read_resource("file:///test.txt")

    with pytest.raises(RuntimeError, match="Actor is not initialized"):
        await workbench.list_resource_templates()
