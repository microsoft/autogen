"""Tests for OpenAI agent builtin tool validation."""

# Standard library imports
import os
from typing import Any, Dict, cast

# Third-party imports
import pytest

# Local imports
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.agents.openai import OpenAIAgent
from openai import AsyncOpenAI
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def set_dummy_openai_key(monkeypatch: MonkeyPatch) -> None:
    """Ensure tests have a dummy OPENAI_API_KEY by default."""
    # Only set a dummy key if no api key is provided
    if not os.getenv("OPENAI_API_KEY"):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")


skip_if_no_real_openai_key = pytest.mark.skipif(
    os.getenv("OPENAI_API_KEY", "") in ("", "sk-test-dummy-key"),
    reason="No real OPENAI_API_KEY provided; skipping integration test.",
)


@pytest.fixture
def openai_client() -> AsyncOpenAI:
    """Provides an AsyncOpenAI client using the test API key."""
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


@pytest.fixture
def cancel_token() -> CancellationToken:
    """Provides a fresh CancellationToken for each test."""
    return CancellationToken()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,model,should_raise",
    [
        ("web_search_preview", "gpt-4o", False),
        ("image_generation", "gpt-4o", False),
        ("local_shell", "codex-mini-latest", False),
        ("local_shell", "gpt-4o", True),
        ("file_search", "gpt-4o", True),
        ("code_interpreter", "gpt-4o", True),
        ("computer_use_preview", "gpt-4o", True),
        ("mcp", "gpt-4o", True),
        ("not_a_tool", "gpt-4o", True),
    ],
)
async def test_builtin_tool_string_validation(
    tool_name: str, model: str, should_raise: bool, openai_client: AsyncOpenAI
) -> None:
    """Test validation of string-based builtin tools."""
    client = openai_client
    tools = [tool_name]  # type: ignore

    if should_raise:
        with pytest.raises(ValueError):
            OpenAIAgent(
                name="test",
                description="desc",
                client=client,
                model=model,
                instructions="inst",
                tools=tools,  # type: ignore
            )
    else:
        agent = OpenAIAgent(
            name="test",
            description="desc",
            client=client,
            model=model,
            instructions="inst",
            tools=tools,  # type: ignore
        )
        assert any(t["type"] == tool_name for t in agent.tools)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_config,should_raise",
    [
        # file_search: missing required param
        ({"type": "file_search"}, True),
        # file_search: empty vector_store_ids
        ({"type": "file_search", "vector_store_ids": []}, True),
        # file_search: invalid type
        ({"type": "file_search", "vector_store_ids": [123]}, True),
        # file_search: valid
        ({"type": "file_search", "vector_store_ids": ["vs1"]}, False),
        # computer_use_preview: missing param
        ({"type": "computer_use_preview", "display_height": 100, "display_width": 100}, True),
        # computer_use_preview: invalid type
        ({"type": "computer_use_preview", "display_height": -1, "display_width": 100, "environment": "desktop"}, True),
        # computer_use_preview: valid
        (
            {"type": "computer_use_preview", "display_height": 100, "display_width": 100, "environment": "desktop"},
            False,
        ),
        # code_interpreter: missing param
        ({"type": "code_interpreter"}, True),
        # code_interpreter: empty container
        ({"type": "code_interpreter", "container": ""}, True),
        # code_interpreter: valid
        ({"type": "code_interpreter", "container": "python-3.11"}, False),
        # mcp: missing param
        ({"type": "mcp", "server_label": "label"}, True),
        # mcp: invalid type
        ({"type": "mcp", "server_label": "", "server_url": "url"}, True),
        # mcp: valid
        ({"type": "mcp", "server_label": "label", "server_url": "url"}, False),
        # web_search_preview: valid with string user_location
        ({"type": "web_search_preview", "user_location": "US"}, False),
        # web_search_preview: valid with dict user_location
        ({"type": "web_search_preview", "user_location": {"type": "approximate"}}, False),
        # web_search_preview: invalid user_location type
        ({"type": "web_search_preview", "user_location": 123}, True),
        # image_generation: valid with background
        ({"type": "image_generation", "background": "white"}, False),
        # image_generation: invalid background
        ({"type": "image_generation", "background": ""}, True),
    ],
)
async def test_builtin_tool_dict_validation(
    tool_config: Dict[str, Any], should_raise: bool, openai_client: AsyncOpenAI
) -> None:
    """Test validation of dictionary-based builtin tools."""
    client = openai_client
    tools = [tool_config]  # type: ignore

    if should_raise:
        with pytest.raises(ValueError):
            OpenAIAgent(
                name="test",
                description="desc",
                client=client,
                model="gpt-4o",
                instructions="inst",
                tools=tools,  # type: ignore
            )
    else:
        agent = OpenAIAgent(
            name="test",
            description="desc",
            client=client,
            model="gpt-4o",
            instructions="inst",
            tools=tools,  # type: ignore
        )
        assert any(t["type"] == tool_config["type"] for t in agent.tools)


@pytest.mark.asyncio
async def test_builtin_tool_validation_with_custom_and_builtin(openai_client: AsyncOpenAI) -> None:
    """Test validation with mixed string and dictionary tools."""
    client = openai_client
    tools = ["web_search_preview", {"type": "image_generation"}]  # type: ignore
    agent = OpenAIAgent(
        name="test",
        description="desc",
        client=client,
        model="gpt-4o",
        instructions="inst",
        tools=tools,  # type: ignore
    )
    assert any(t["type"] == "web_search_preview" for t in agent.tools)
    assert any(t["type"] == "image_generation" for t in agent.tools)


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_with_openai_api() -> None:
    """Test basic integration with OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = ["web_search_preview"]  # type: ignore
    agent = OpenAIAgent(
        name="integration",
        description="desc",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()
    response = await agent.on_messages(
        [TextMessage(source="user", content="What is the capital of France?")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert content


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_web_search_preview_tool() -> None:
    """Test web_search_preview tool with actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = ["web_search_preview"]  # type: ignore
    agent = OpenAIAgent(
        name="web_search_test",
        description="Test agent with web search capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with web search capabilities. Use web search when needed.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test web search functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="What are the latest developments in AI technology?")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_image_generation_tool() -> None:
    """Test image_generation tool with actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = ["image_generation"]  # type: ignore
    agent = OpenAIAgent(
        name="image_gen_test",
        description="Test agent with image generation capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with image generation capabilities. Generate images when requested.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test image generation functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="Generate an image of a beautiful sunset over mountains")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_configured_web_search_tool() -> None:
    """Test web_search_preview tool with configuration using actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = [{"type": "web_search_preview", "user_location": "US", "search_context_size": 5}]  # type: ignore
    agent = OpenAIAgent(
        name="configured_web_search_test",
        description="Test agent with configured web search capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with configured web search capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test configured web search functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="What's the weather like in San Francisco today?")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_configured_image_generation_tool() -> None:
    """Test image_generation tool with configuration using actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = [{"type": "image_generation", "background": "white"}]  # type: ignore
    agent = OpenAIAgent(
        name="configured_image_gen_test",
        description="Test agent with configured image generation capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with configured image generation capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test configured image generation functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="Create an image of a cat sitting on a white background")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_multiple_builtin_tools() -> None:
    """Test multiple builtin tools together with actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = ["web_search_preview", "image_generation"]  # type: ignore
    agent = OpenAIAgent(
        name="multi_tool_test",
        description="Test agent with multiple builtin tools",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with web search and image generation capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test multiple tools functionality
    response = await agent.on_messages(
        [
            TextMessage(
                source="user",
                content="Search for information about space exploration and generate an image of a rocket",
            )
        ],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_file_search_tool_with_vector_store() -> None:
    """Test file_search tool with vector store configuration (requires actual vector store)."""
    api_key = os.getenv("OPENAI_API_KEY")

    # Skip this test if no vector store ID is provided
    vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if not vector_store_id:
        pytest.skip("OPENAI_VECTOR_STORE_ID not set; skipping file_search integration test.")

    client = AsyncOpenAI(api_key=api_key)
    tools = [{"type": "file_search", "vector_store_ids": [vector_store_id]}]  # type: ignore
    agent = OpenAIAgent(
        name="file_search_test",
        description="Test agent with file search capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with file search capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test file search functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="Search for documents about machine learning")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_code_interpreter_tool() -> None:
    """Test code_interpreter tool with actual API call."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = [{"type": "code_interpreter", "container": "python-3.11"}]  # type: ignore
    agent = OpenAIAgent(
        name="code_interpreter_test",
        description="Test agent with code interpreter capability",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with code execution capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test code interpreter functionality
    response = await agent.on_messages(
        [TextMessage(source="user", content="Calculate the sum of numbers from 1 to 100")],
        cancellation_token,
    )
    assert hasattr(response, "chat_message")
    assert hasattr(response.chat_message, "content")
    content = getattr(response.chat_message, "content", "")
    assert len(content) > 0


@pytest.mark.asyncio
@skip_if_no_real_openai_key
async def test_integration_streaming_with_builtin_tools() -> None:
    """Test streaming responses with builtin tools."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    tools = ["web_search_preview"]  # type: ignore
    agent = OpenAIAgent(
        name="streaming_test",
        description="Test agent with streaming and builtin tools",
        client=client,
        model="gpt-4o",
        instructions="You are a helpful assistant with web search capabilities.",
        tools=tools,  # type: ignore
    )
    cancellation_token = CancellationToken()

    # Test streaming with builtin tools
    messages: list[Any] = []
    async for message in agent.on_messages_stream(
        [TextMessage(source="user", content="What are the latest news about renewable energy?")],
        cancellation_token,
    ):
        messages.append(message)

    # Verify we received some messages
    assert len(messages) > 0
    # Verify at least one message has content
    content_messages = [
        msg
        for msg in messages
        if hasattr(msg, "chat_message")
        and hasattr(msg.chat_message, "content")
        and getattr(msg.chat_message, "content", False)
    ]
    assert len(content_messages) > 0


# JSON Config Tests for Built-in Tools


@pytest.mark.asyncio
async def test_to_config_with_string_builtin_tools() -> None:
    """Test _to_config with string-based builtin tools."""
    client = AsyncOpenAI()
    tools = ["web_search_preview", "image_generation"]  # type: ignore
    agent = OpenAIAgent(
        name="config_test",
        description="Test agent for config serialization",
        client=client,
        model="gpt-4o",
        instructions="Test instructions",
        tools=tools,  # type: ignore
    )

    config = agent.to_config()
    assert config.name == "config_test"
    assert config.description == "Test agent for config serialization"
    assert config.model == "gpt-4o"
    assert config.instructions == "Test instructions"
    assert config.tools is not None
    assert len(config.tools) == 2

    # Verify tools are serialized correctly
    tool_types: list[str] = []
    for tool in config.tools:
        if isinstance(tool, str):
            tool_types.append(tool)
        elif isinstance(tool, dict):
            tool_types.append(cast(Dict[str, Any], tool)["type"])
        else:
            # Handle ComponentModel case
            tool_types.append(str(tool))
    assert "web_search_preview" in tool_types
    assert "image_generation" in tool_types


@pytest.mark.asyncio
async def test_to_config_with_configured_builtin_tools() -> None:
    """Test _to_config with configured builtin tools."""
    client = AsyncOpenAI()
    tools = [
        {"type": "file_search", "vector_store_ids": ["vs1", "vs2"], "max_num_results": 10},  # type: ignore
        {"type": "web_search_preview", "user_location": "US", "search_context_size": 5},  # type: ignore
        {"type": "image_generation", "background": "white"},  # type: ignore
    ]
    agent = OpenAIAgent(
        name="configured_test",
        description="Test agent with configured tools",
        client=client,
        model="gpt-4o",
        instructions="Test instructions",
        tools=tools,  # type: ignore
    )

    config = agent.to_config()
    assert config.name == "configured_test"
    assert config.tools is not None
    assert len(config.tools) == 3

    # Verify configured tools are serialized correctly
    tool_configs = [cast(Dict[str, Any], tool) for tool in config.tools if isinstance(tool, dict)]
    assert len(tool_configs) == 3

    # Check file_search config
    file_search_config = next(tool for tool in tool_configs if tool["type"] == "file_search")
    assert file_search_config["vector_store_ids"] == ["vs1", "vs2"]
    assert file_search_config["max_num_results"] == 10

    # Check web_search_preview config
    web_search_config = next(tool for tool in tool_configs if tool["type"] == "web_search_preview")
    assert web_search_config["user_location"] == "US"
    assert web_search_config["search_context_size"] == 5

    # Check image_generation config
    image_gen_config = next(tool for tool in tool_configs if tool["type"] == "image_generation")
    assert image_gen_config["background"] == "white"


@pytest.mark.asyncio
async def test_from_config_with_string_builtin_tools() -> None:
    """Test _from_config with string-based builtin tools."""
    from autogen_ext.agents.openai._openai_agent import OpenAIAgentConfig  # type: ignore

    config = OpenAIAgentConfig(
        name="from_config_test",
        description="Test agent from config",
        model="gpt-4o",
        instructions="Test instructions",
        tools=["web_search_preview", "image_generation"],  # type: ignore
    )
    agent = OpenAIAgent.from_config(config)
    assert agent.name == "from_config_test"
    assert agent.description == "Test agent from config"
    assert agent.model == "gpt-4o"
    # Verify instructions via configuration
    assert agent.to_config().instructions == "Test instructions"
    # Verify tools are loaded correctly
    assert len(agent.tools) == 2
    tool_types = [tool["type"] for tool in agent.tools]
    assert "web_search_preview" in tool_types
    assert "image_generation" in tool_types


@pytest.mark.asyncio
async def test_from_config_with_configured_builtin_tools() -> None:
    """Test _from_config with configured builtin tools."""
    from autogen_ext.agents.openai._openai_agent import OpenAIAgentConfig  # type: ignore

    config = OpenAIAgentConfig(
        name="configured_from_config_test",
        description="Test agent with configured tools from config",
        model="gpt-4o",
        instructions="Test instructions",
        tools=[
            {"type": "file_search", "vector_store_ids": ["vs1"]},  # type: ignore
            {"type": "web_search_preview", "user_location": "US"},  # type: ignore
            {"type": "image_generation", "background": "black"},  # type: ignore
        ],
    )
    agent = OpenAIAgent.from_config(config)
    assert agent.name == "configured_from_config_test"
    assert agent.model == "gpt-4o"
    # Verify configured tools are loaded correctly
    assert len(agent.tools) == 3
    # Check file_search
    file_search_tool = next(tool for tool in agent.tools if tool["type"] == "file_search")
    assert file_search_tool["vector_store_ids"] == ["vs1"]
    # Check web_search_preview
    web_search_tool = next(tool for tool in agent.tools if tool["type"] == "web_search_preview")
    assert web_search_tool["user_location"] == "US"
    # Check image_generation
    image_gen_tool = next(tool for tool in agent.tools if tool["type"] == "image_generation")
    assert image_gen_tool["background"] == "black"


@pytest.mark.asyncio
async def test_round_trip_config_serialization() -> None:
    """Test round-trip serialization: agent -> config -> agent."""
    client = AsyncOpenAI()
    original_tools = [
        "web_search_preview",
        {"type": "file_search", "vector_store_ids": ["vs1"]},  # type: ignore
        {"type": "image_generation", "background": "white"},  # type: ignore
    ]

    original_agent = OpenAIAgent(
        name="round_trip_test",
        description="Test round-trip serialization",
        client=client,
        model="gpt-4o",
        instructions="Test instructions",
        tools=original_tools,  # type: ignore
    )

    # Serialize to config
    config = original_agent.to_config()

    # Deserialize back to agent
    restored_agent = OpenAIAgent.from_config(config)

    # Verify basic properties
    assert restored_agent.name == original_agent.name
    assert restored_agent.description == original_agent.description
    assert restored_agent.model == original_agent.model
    orig_config = original_agent.to_config()
    restored_config = restored_agent.to_config()
    assert restored_config.instructions == orig_config.instructions

    # Verify tools are preserved
    assert len(restored_agent.tools) == len(original_agent.tools)

    # Check that string tools are preserved
    assert any(tool["type"] == "web_search_preview" for tool in restored_agent.tools)

    # Check that configured tools are preserved
    file_search_tool = next(tool for tool in restored_agent.tools if tool["type"] == "file_search")
    assert file_search_tool["vector_store_ids"] == ["vs1"]

    image_gen_tool = next(tool for tool in restored_agent.tools if tool["type"] == "image_generation")
    assert image_gen_tool["background"] == "white"


@pytest.mark.asyncio
async def test_config_serialization_with_mixed_tools() -> None:
    """Test config serialization with mixed string and configured tools."""
    client = AsyncOpenAI()
    tools = [
        "web_search_preview",  # string tool
        {"type": "file_search", "vector_store_ids": ["vs1"]},  # type: ignore
        "image_generation",  # string tool
        {"type": "code_interpreter", "container": "python-3.11"},  # type: ignore
    ]

    agent = OpenAIAgent(
        name="mixed_tools_test",
        description="Test agent with mixed tool types",
        client=client,
        model="gpt-4o",
        instructions="Test instructions",
        tools=tools,  # type: ignore
    )

    config = agent.to_config()
    assert config.tools is not None
    assert len(config.tools) == 4

    # Verify all tools are serialized as dicts with "type" key
    dict_tools = [cast(Dict[str, Any], tool) for tool in config.tools if isinstance(tool, dict)]
    assert len(dict_tools) == 4

    # Check that string tools are converted to dicts with "type" key
    tool_types = [tool["type"] for tool in dict_tools]
    assert "web_search_preview" in tool_types
    assert "file_search" in tool_types
    assert "image_generation" in tool_types
    assert "code_interpreter" in tool_types

    # Verify configured tools preserve their configuration
    file_search_config = next(tool for tool in dict_tools if tool["type"] == "file_search")
    assert file_search_config["vector_store_ids"] == ["vs1"]

    code_interpreter_config = next(tool for tool in dict_tools if tool["type"] == "code_interpreter")
    assert code_interpreter_config["container"] == "python-3.11"


@pytest.mark.asyncio
async def test_config_serialization_with_local_shell() -> None:
    """Test config serialization with local_shell tool (model-restricted)."""
    client = AsyncOpenAI()
    tools = ["local_shell"]  # type: ignore

    agent = OpenAIAgent(
        name="local_shell_test",
        description="Test agent with local_shell",
        client=client,
        model="codex-mini-latest",  # Required for local_shell
        instructions="Test instructions",
        tools=tools,  # type: ignore
    )

    config = agent.to_config()
    assert config.model == "codex-mini-latest"
    assert config.tools is not None
    assert len(config.tools) == 1
    # Built-in tools are serialized as dicts with "type" key
    assert config.tools[0] == {"type": "local_shell"}

    # Test round-trip
    restored_agent = OpenAIAgent.from_config(config)
    assert restored_agent.model == "codex-mini-latest"
    assert len(restored_agent.tools) == 1
    assert restored_agent.tools[0]["type"] == "local_shell"


@pytest.mark.asyncio
async def test_config_serialization_with_complex_web_search() -> None:
    """Test config serialization with complex web_search_preview configuration."""
    client = AsyncOpenAI()
    tools = [
        {
            "type": "web_search_preview",
            "user_location": {"type": "approximate", "country": "US", "region": "CA", "city": "San Francisco"},
            "search_context_size": 10,
        }
    ]  # type: ignore
    agent = OpenAIAgent(
        name="complex_web_search_test",
        description="Test agent with complex web search config",
        client=client,
        model="gpt-4o",
        instructions="Test instructions",
        tools=tools,  # type: ignore
    )
    config = agent.to_config()
    assert config.tools is not None
    assert len(config.tools) == 1
    web_search_config = cast(Dict[str, Any], config.tools[0])
    assert isinstance(web_search_config, dict)
    assert web_search_config["type"] == "web_search_preview"
    user_location = web_search_config["user_location"]
    if isinstance(user_location, dict):
        assert user_location["type"] == "approximate"
        assert user_location["country"] == "US"
        assert user_location["region"] == "CA"
        assert user_location["city"] == "San Francisco"
    else:
        # If user_location is a string, just check value
        assert user_location == "US"
    assert web_search_config["search_context_size"] == 10
    # Test round-trip
    restored_agent = OpenAIAgent.from_config(config)
    restored_tool = cast(Dict[str, Any], restored_agent.tools[0])
    assert restored_tool["type"] == "web_search_preview"
    restored_user_location = restored_tool["user_location"]
    if isinstance(restored_user_location, dict):
        assert restored_user_location["type"] == "approximate"
        assert restored_user_location["country"] == "US"
        assert restored_user_location["region"] == "CA"
        assert restored_user_location["city"] == "San Francisco"
    else:
        assert restored_user_location == "US"
    assert restored_tool["search_context_size"] == 10
