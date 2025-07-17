import asyncio
from typing import Any, AsyncGenerator, Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import Component
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from mcp.types import CallToolResult, ListToolsResult, TextContent
from mcp.types import Tool as McpTool
from pydantic import BaseModel


class MockChatCompletionClientConfig(BaseModel):
    model_info: ModelInfo


class MockChatCompletionClient(ChatCompletionClient, Component[MockChatCompletionClientConfig]):
    """Mock chat completion client for testing."""

    component_type = "test"
    component_config_schema = MockChatCompletionClientConfig
    component_provider_override = f"{__module__}.MockChatCompletionClient"

    def __init__(self, model_info: ModelInfo | None = None):
        self._model_info = model_info or {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "test-model",
            "structured_output": False,
        }

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    async def create(self, *args: Any, **kwargs: Any) -> CreateResult:
        return CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )

    def create_stream(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str | CreateResult, None]:
        async def mock_stream() -> AsyncGenerator[str | CreateResult, None]:
            yield "Mock streaming response"
            yield CreateResult(
                content="Mock response",
                finish_reason="stop",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )

        return mock_stream()

    async def close(self) -> None:
        pass

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 10

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return 1000

    @property
    def capabilities(self) -> Any:  # ModelCapabilities is deprecated
        return {}

    def _to_config(self) -> BaseModel:
        return MockChatCompletionClientConfig(model_info=self.model_info)

    @classmethod
    def _from_config(cls, config: MockChatCompletionClientConfig) -> "MockChatCompletionClient":
        return cls(config.model_info)


@pytest.fixture
def sample_mcp_tools() -> list[McpTool]:
    """Create sample MCP tools for testing."""
    return [
        McpTool(
            name="test_tool",
            description="A test tool",
            inputSchema={
                "type": "object",
                "properties": {"param": {"type": "string"}},
                "required": ["param"],
            },
        ),
    ]


@pytest.fixture
def mock_mcp_actor() -> AsyncMock:
    """Mock MCP session actor."""
    actor = AsyncMock()
    return actor


@pytest.fixture
def sample_server_params() -> StdioServerParams:
    """Sample server parameters for testing."""
    return StdioServerParams(command="echo", args=["test"])


@pytest.fixture
def mock_model_client() -> MockChatCompletionClient:
    """Mock model client for testing."""
    model_client = MockChatCompletionClient()
    # Set up the mock's create method
    mock_create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    model_client.create = mock_create  # type: ignore[method-assign]
    return model_client


@pytest.fixture
def mock_model_client_with_vision() -> MockChatCompletionClient:
    """Mock model client with vision support for testing."""
    model_client = MockChatCompletionClient(
        model_info={
            "vision": True,
            "function_calling": False,
            "json_output": False,
            "family": "test-vision-model",
            "structured_output": False,
        }
    )
    # Set up the mock's create method
    mock_create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    model_client.create = mock_create  # type: ignore[method-assign]
    return model_client


@pytest.mark.asyncio
async def test_mcp_workbench_with_model_client_initialization(
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test McpWorkbench initialization with a model client."""
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    assert workbench._model_client is mock_model_client  # type: ignore[attr-defined]

    # Test that the workbench is properly configured
    config = workbench._to_config()  # type: ignore[attr-defined]
    assert config.model_client is not None
    assert config.server_params == sample_server_params


@pytest.mark.asyncio
async def test_mcp_workbench_without_model_client_initialization(
    sample_server_params: StdioServerParams,
) -> None:
    """Test McpWorkbench initialization without a model client."""
    workbench = McpWorkbench(server_params=sample_server_params)

    assert workbench._model_client is None  # type: ignore[attr-defined]

    # Test that the workbench is properly configured
    config = workbench._to_config()  # type: ignore[attr-defined]
    assert config.model_client is None
    assert config.server_params == sample_server_params


@pytest.mark.asyncio
async def test_mcp_workbench_serialization_with_model_client(
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test serialization and deserialization of McpWorkbench with model client."""
    # Create original workbench
    original_workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    # Serialize to config
    config = original_workbench._to_config()  # type: ignore[attr-defined]
    assert config.model_client is not None

    # Deserialize from config
    loaded_workbench = McpWorkbench._from_config(config)  # type: ignore[attr-defined]

    # Verify the loaded workbench
    assert loaded_workbench.server_params == sample_server_params
    assert loaded_workbench._model_client is not None  # type: ignore[attr-defined]
    assert loaded_workbench._model_client.model_info == mock_model_client.model_info  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_serialization_without_model_client(
    sample_server_params: StdioServerParams,
) -> None:
    """Test serialization and deserialization of McpWorkbench without model client."""
    # Create original workbench
    original_workbench = McpWorkbench(server_params=sample_server_params)

    # Serialize to config
    config = original_workbench._to_config()  # type: ignore[attr-defined]
    assert config.model_client is None

    # Deserialize from config
    loaded_workbench = McpWorkbench._from_config(config)  # type: ignore[attr-defined]

    # Verify the loaded workbench
    assert loaded_workbench.server_params == sample_server_params
    assert loaded_workbench._model_client is None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_model_client_passed_to_actor(
    sample_mcp_tools: list[McpTool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that model client is properly passed to the MCP actor."""
    # Mock the McpSessionActor creation
    mock_actor_class = MagicMock()
    mock_actor_instance = mock_mcp_actor
    mock_actor_class.return_value = mock_actor_instance

    monkeypatch.setattr("autogen_ext.tools.mcp._workbench.McpSessionActor", mock_actor_class)

    # Create workbench with model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    future_result: asyncio.Future[ListToolsResult] = asyncio.Future()
    future_result.set_result(list_tools_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Start the workbench - this should create the actor with the model client
        await workbench.start()

        # Verify that the actor was created with the model client
        mock_actor_class.assert_called_once_with(sample_server_params, model_client=mock_model_client)

        # Verify that initialize was called on the actor
        mock_mcp_actor.initialize.assert_called_once()

    finally:
        if workbench._actor:  # type: ignore[attr-defined]
            workbench._actor = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_start_without_explicit_model_client(
    sample_mcp_tools: list[McpTool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that actor is created correctly when no model client is provided."""
    # Mock the McpSessionActor creation
    mock_actor_class = MagicMock()
    mock_actor_instance = mock_mcp_actor
    mock_actor_class.return_value = mock_actor_instance

    monkeypatch.setattr("autogen_ext.tools.mcp._workbench.McpSessionActor", mock_actor_class)

    # Create workbench without model client
    workbench = McpWorkbench(server_params=sample_server_params)

    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    future_result: asyncio.Future[ListToolsResult] = asyncio.Future()
    future_result.set_result(list_tools_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Start the workbench - this should create the actor without model client
        await workbench.start()

        # Verify that the actor was created without the model client
        mock_actor_class.assert_called_once_with(sample_server_params, model_client=None)

        # Verify that initialize was called on the actor
        mock_mcp_actor.initialize.assert_called_once()

    finally:
        if workbench._actor:  # type: ignore[attr-defined]
            workbench._actor = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_list_tools_with_model_client(
    sample_mcp_tools: list[McpTool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test that list_tools works correctly with model client."""
    # Create workbench with model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )
    workbench._actor = mock_mcp_actor  # type: ignore[attr-defined]

    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    future_result: asyncio.Future[ListToolsResult] = asyncio.Future()
    future_result.set_result(list_tools_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # List tools
        tools = await workbench.list_tools()

        # Verify tools are returned correctly
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        assert tools[0].get("description") == "A test tool"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("list_tools", None)

    finally:
        workbench._actor = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_call_tool_with_model_client(
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test that call_tool works correctly with model client."""
    # Create workbench with model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )
    workbench._actor = mock_mcp_actor  # type: ignore[attr-defined]

    # Mock call_tool response
    call_tool_result = CallToolResult(
        content=[TextContent(type="text", text="Tool executed successfully")],
        isError=False,
    )
    future_result: asyncio.Future[CallToolResult] = asyncio.Future()
    future_result.set_result(call_tool_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Call tool
        result = await workbench.call_tool(
            name="test_tool",
            arguments={"param": "test_value"},
        )

        # Verify result
        assert not result.is_error
        assert len(result.result) == 1
        assert result.result[0].content == "Tool executed successfully"

        # Verify actor was called correctly
        mock_mcp_actor.call.assert_called_with("call_tool", {"name": "test_tool", "kargs": {"param": "test_value"}})

    finally:
        workbench._actor = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_state_operations_with_model_client(
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test state save/load operations with model client."""
    # Create workbench with model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    # Save state
    state = await workbench.save_state()
    assert state["type"] == "McpWorkBenchState"

    # Load state (should not affect model client)
    await workbench.load_state(state)

    # Model client should still be there
    assert workbench._model_client is mock_model_client  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_fallback_start_behavior(
    sample_mcp_tools: list[McpTool],
    mock_mcp_actor: AsyncMock,
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test fallback start behavior when actor is not initialized."""
    # Mock the McpSessionActor creation
    mock_actor_class = MagicMock()
    mock_actor_instance = mock_mcp_actor
    mock_actor_class.return_value = mock_actor_instance

    monkeypatch.setattr("autogen_ext.tools.mcp._workbench.McpSessionActor", mock_actor_class)

    # Create workbench with model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    # Ensure actor is not initialized
    assert workbench._actor is None  # type: ignore[attr-defined]

    # Mock list_tools response
    list_tools_result = ListToolsResult(tools=sample_mcp_tools)
    future_result: asyncio.Future[ListToolsResult] = asyncio.Future()
    future_result.set_result(list_tools_result)
    mock_mcp_actor.call.return_value = future_result

    try:
        # Call list_tools without explicitly starting - should auto-start
        tools = await workbench.list_tools()

        # Verify that the actor was created with the model client
        mock_actor_class.assert_called_once_with(sample_server_params, model_client=mock_model_client)

        # Verify that initialize was called on the actor
        mock_mcp_actor.initialize.assert_called_once()

        # Verify tools are returned correctly
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    finally:
        if workbench._actor:  # type: ignore[attr-defined]
            workbench._actor = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_model_client_vision_support(
    sample_server_params: StdioServerParams,
    mock_model_client_with_vision: MockChatCompletionClient,
) -> None:
    """Test that model client with vision support is properly configured."""
    # Create workbench with vision-enabled model client
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client_with_vision,
    )

    # Verify model client has vision capabilities
    assert workbench._model_client is not None  # type: ignore[attr-defined]
    assert workbench._model_client.model_info["vision"] is True  # type: ignore[attr-defined]
    assert workbench._model_client.model_info["family"] == "test-vision-model"  # type: ignore[attr-defined]

    # Test serialization preserves vision capabilities
    config = workbench._to_config()  # type: ignore[attr-defined]
    loaded_workbench = McpWorkbench._from_config(config)  # type: ignore[attr-defined]

    assert loaded_workbench._model_client is not None  # type: ignore[attr-defined]
    assert loaded_workbench._model_client.model_info["vision"] is True  # type: ignore[attr-defined]
    assert loaded_workbench._model_client.model_info["family"] == "test-vision-model"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_workbench_component_interface(
    sample_server_params: StdioServerParams,
    mock_model_client: MockChatCompletionClient,
) -> None:
    """Test that McpWorkbench properly implements the Component interface."""
    # Test component provider override
    assert McpWorkbench.component_provider_override == "autogen_ext.tools.mcp.McpWorkbench"

    # Test config schema
    config_schema = McpWorkbench.component_config_schema
    assert config_schema is not None

    # Test serialization/deserialization through component interface
    workbench = McpWorkbench(
        server_params=sample_server_params,
        model_client=mock_model_client,
    )

    # Test _to_config
    config = workbench._to_config()  # type: ignore[attr-defined]
    assert hasattr(config, "server_params")
    assert hasattr(config, "model_client")
    assert hasattr(config, "tool_overrides")

    # Test _from_config
    loaded_workbench = McpWorkbench._from_config(config)  # type: ignore[attr-defined]
    assert loaded_workbench.server_params == sample_server_params
    assert loaded_workbench._model_client is not None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_sampling_callback_invocation(
    mock_model_client: MockChatCompletionClient, sample_server_params: StdioServerParams
) -> None:
    """Test that the sampling_callback in McpSessionActor is actually called when requested."""
    from unittest.mock import MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, CreateMessageResult, SamplingMessage, TextContent

    # Set up the mock for this specific test
    mock_create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    mock_model_client.create = mock_create  # type: ignore[method-assign]

    # Create an actor with a model client
    actor = McpSessionActor(sample_server_params, model_client=mock_model_client)

    # Create mock request context and parameters for sampling
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(type="text", text="Hello, how are you?"))],
        maxTokens=100,
    )

    # Test the sampling callback directly
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result is a CreateMessageResult (not an error)
    assert isinstance(result, CreateMessageResult)
    assert result.role == "assistant"
    assert result.content.type == "text"
    assert result.content.text == "Mock response"
    assert result.model == "test-model"
    assert result.stopReason == "stop"

    # Verify the model client was called correctly
    assert mock_create.called
    # Get the call arguments
    call_args = mock_create.call_args
    messages = call_args.kwargs["messages"]  # Messages are passed as keyword argument
    assert len(messages) == 1
    assert messages[0].source == "user"
    assert "Hello, how are you?" in str(messages[0].content)


@pytest.mark.asyncio
async def test_sampling_callback_without_model_client(sample_server_params: StdioServerParams) -> None:
    """Test that sampling_callback returns error when no model client is provided."""
    from unittest.mock import MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, ErrorData, SamplingMessage, TextContent

    # Create an actor without a model client
    actor = McpSessionActor(sample_server_params, model_client=None)

    # Create mock request context and parameters
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(type="text", text="Hello, how are you?"))],
        maxTokens=100,
    )

    # Test the sampling callback
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result is an ErrorData (indicating no model client)
    assert isinstance(result, ErrorData)


@pytest.mark.asyncio
async def test_sampling_callback_with_system_prompt(
    mock_model_client: MockChatCompletionClient, sample_server_params: StdioServerParams
) -> None:
    """Test sampling_callback with system prompt."""
    from unittest.mock import MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, CreateMessageResult, SamplingMessage, TextContent

    # Set up the mock for this specific test
    mock_create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    mock_model_client.create = mock_create  # type: ignore[method-assign]

    # Create an actor with a model client
    actor = McpSessionActor(sample_server_params, model_client=mock_model_client)

    # Create mock request context and parameters with system prompt
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(type="text", text="What's the weather?"))],
        systemPrompt="You are a helpful weather assistant.",
        maxTokens=100,
    )

    # Test the sampling callback
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result
    assert isinstance(result, CreateMessageResult)

    # Verify the model client was called with system prompt
    assert mock_create.called
    call_args = mock_create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) == 2  # system + user message

    # Check system message
    system_msg = messages[0]
    assert system_msg.__class__.__name__ == "SystemMessage"
    assert "helpful weather assistant" in str(system_msg.content)

    # Check user message
    user_msg = messages[1]
    assert user_msg.source == "user"
    assert "weather" in str(user_msg.content)


@pytest.mark.asyncio
async def test_sampling_callback_with_image_content(
    mock_model_client_with_vision: MockChatCompletionClient, sample_server_params: StdioServerParams
) -> None:
    """Test sampling_callback with image content when vision is supported."""
    from unittest.mock import MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, CreateMessageResult, ImageContent, SamplingMessage

    # Set up the mock for this specific test
    mock_create = AsyncMock(
        return_value=CreateResult(
            content="Mock response",
            finish_reason="stop",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            cached=False,
        )
    )
    mock_model_client_with_vision.create = mock_create  # type: ignore[method-assign]

    # Create an actor with a vision-capable model client
    actor = McpSessionActor(sample_server_params, model_client=mock_model_client_with_vision)

    # Create a simple test image (1x1 pixel PNG) - using a proper PNG
    # This is a valid 1x1 transparent PNG
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    # Create mock request context and parameters with image
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[
            SamplingMessage(role="user", content=ImageContent(type="image", data=test_image_b64, mimeType="image/png"))
        ],
        maxTokens=100,
    )

    # Test the sampling callback
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result
    assert isinstance(result, CreateMessageResult)

    # Verify the model client was called
    assert mock_create.called
    call_args = mock_create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) == 1

    # Check that the message contains image content
    user_msg = messages[0]
    assert user_msg.source == "user"
    # The content should be a list containing an Image object
    assert isinstance(user_msg.content, list)
    assert len(user_msg.content) == 1  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_sampling_callback_image_without_vision_support(
    mock_model_client: MockChatCompletionClient, sample_server_params: StdioServerParams
) -> None:
    """Test sampling_callback fails gracefully when image is sent to non-vision model."""
    from unittest.mock import MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, ErrorData, ImageContent, SamplingMessage

    # Create an actor with a non-vision model client
    actor = McpSessionActor(sample_server_params, model_client=mock_model_client)

    # Create a simple test image - using the same valid PNG
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    # Create mock request context and parameters with image
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[
            SamplingMessage(role="user", content=ImageContent(type="image", data=test_image_b64, mimeType="image/png"))
        ],
        maxTokens=100,
    )

    # Test the sampling callback
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result is an error due to vision not being supported
    assert isinstance(result, ErrorData)
    # Check both the message and data fields for vision/image-related error
    error_text = (result.message + " " + str(result.data or "")).lower()
    assert "vision" in error_text or "image" in error_text


@pytest.mark.asyncio
async def test_sampling_callback_model_client_error(sample_server_params: StdioServerParams) -> None:
    """Test sampling_callback handles model client errors gracefully."""
    from unittest.mock import AsyncMock, MagicMock

    from autogen_ext.tools.mcp._actor import McpSessionActor
    from mcp.shared.context import RequestContext
    from mcp.types import CreateMessageRequestParams, ErrorData, SamplingMessage, TextContent

    # Create a model client that will fail
    failing_model_client = MockChatCompletionClient()
    failing_model_client.create = AsyncMock(side_effect=Exception("Model API error"))  # type: ignore[method-assign]

    # Create an actor with the failing model client
    actor = McpSessionActor(sample_server_params, model_client=failing_model_client)

    # Create mock request context and parameters
    mock_context = MagicMock(spec=RequestContext)
    sample_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(type="text", text="Hello"))], maxTokens=100
    )

    # Test the sampling callback
    result = await actor._sampling_callback(mock_context, sample_params)  # type: ignore[attr-defined]

    # Verify the result is an error
    assert isinstance(result, ErrorData)
    assert result.data is not None and "Model API error" in str(result.data)


@pytest.mark.asyncio
async def test_sampling_callback_integration_through_session(sample_server_params: StdioServerParams) -> None:
    """Test that shows how sampling_callback should work when properly integrated with session."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    # Create a mock model client
    mock_model_client = MagicMock()
    mock_model_client.model_info = {"family": "test", "vision": False}
    mock_model_client.create = AsyncMock(return_value=MagicMock(content="Mock response", finish_reason="stop"))

    # Mock the session creation to verify the sampling_callback is passed
    with patch("autogen_ext.tools.mcp._actor.create_mcp_server_session") as mock_session_factory:
        # Create mock session that properly handles the context manager protocol
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        from autogen_ext.tools.mcp._actor import McpSessionActor

        actor = McpSessionActor(sample_server_params, model_client=mock_model_client)

        # Initialize the actor (this will call create_mcp_server_session)
        await actor.initialize()

        # Wait a moment for the actor to initialize
        await asyncio.sleep(0.1)

        # Verify that the session was created with the sampling_callback
        mock_session_factory.assert_called_once_with(sample_server_params, sampling_callback=actor._sampling_callback)  # type: ignore[attr-defined]

        # Clean up by trying to close the actor gracefully
        if actor._active and actor._actor_task is not None:  # type: ignore[attr-defined]
            try:
                await actor.close()
            except Exception:
                # Ignore cleanup errors since the main assertion passed
                pass
