"""Tests for the Avian model client."""

import json
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import FunctionCall
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import FunctionTool
from autogen_ext.models.avian import AvianChatCompletionClient
from autogen_ext.models.avian._model_info import (
    _MODEL_INFO,
    _MODEL_TOKEN_LIMITS,
    get_info,
    get_token_limit,
    resolve_model,
)


# ---- Model info tests ----


def test_resolve_known_model() -> None:
    assert resolve_model("deepseek/deepseek-v3.2") == "deepseek/deepseek-v3.2"


def test_resolve_model_alias() -> None:
    assert resolve_model("deepseek-v3.2") == "deepseek/deepseek-v3.2"


def test_resolve_unknown_model() -> None:
    assert resolve_model("nonexistent/model") is None


def test_get_info_known_model() -> None:
    info = get_info("deepseek/deepseek-v3.2")
    assert info["function_calling"] is True
    assert info["json_output"] is True
    assert info["vision"] is False


def test_get_info_alias() -> None:
    info = get_info("kimi-k2.5")
    assert info["function_calling"] is True


def test_get_info_unknown_raises() -> None:
    with pytest.raises(KeyError, match="Unknown Avian model"):
        get_info("nonexistent/model")


def test_get_token_limit_known() -> None:
    assert get_token_limit("deepseek/deepseek-v3.2") == 164_000


def test_get_token_limit_alias() -> None:
    assert get_token_limit("minimax-m2.5") == 1_000_000


def test_get_token_limit_unknown_returns_default() -> None:
    assert get_token_limit("nonexistent/model") == 128_000


def test_all_models_have_token_limits() -> None:
    for model in _MODEL_INFO:
        assert model in _MODEL_TOKEN_LIMITS, f"Missing token limit for {model}"


# ---- Client construction tests ----


def test_missing_model_raises() -> None:
    with pytest.raises(ValueError, match="model is required"):
        AvianChatCompletionClient()  # type: ignore


def test_unknown_model_without_info_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    with pytest.raises(ValueError, match="Unknown Avian model"):
        AvianChatCompletionClient(model="nonexistent/model")


def test_unknown_model_with_info_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(
        model="custom/model",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": False,
        },
    )
    assert client.model_info["function_calling"] is True


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AVIAN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key is required"):
        AvianChatCompletionClient(model="deepseek/deepseek-v3.2")


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key-from-env")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    assert client._raw_config["api_key"] == "test-key-from-env"


def test_api_key_from_param(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AVIAN_API_KEY", raising=False)
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2", api_key="direct-key")
    assert client._raw_config["api_key"] == "direct-key"


def test_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    assert str(client._client.base_url).rstrip("/") == "https://api.avian.io/v1"


def test_custom_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2", base_url="https://custom.api/v1")
    assert "custom.api" in str(client._client.base_url)


def test_model_info_auto_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    info = client.model_info
    assert info["function_calling"] is True
    assert info["json_output"] is True
    assert info["vision"] is False


def test_model_info_all_known_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    for model_name in _MODEL_INFO:
        client = AvianChatCompletionClient(model=model_name)
        assert client.model_info is not None


# ---- Serialization tests ----


def test_config_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(
        model="deepseek/deepseek-v3.2",
        api_key="test-key",
        temperature=0.7,
    )
    config = client._to_config()
    assert config.model == "deepseek/deepseek-v3.2"
    assert config.temperature == 0.7


def test_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from autogen_ext.models.avian.config import AvianClientConfigurationConfigModel
    from pydantic import SecretStr

    config = AvianClientConfigurationConfigModel(
        model="deepseek/deepseek-v3.2",
        api_key=SecretStr("test-key"),
        temperature=0.5,
    )
    client = AvianChatCompletionClient._from_config(config)
    assert client._raw_config["model"] == "deepseek/deepseek-v3.2"
    assert client._raw_config["temperature"] == 0.5


# ---- Pickle / state tests ----


def test_getstate_removes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    state = client.__getstate__()
    assert state["_client"] is None


def test_setstate_restores_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")
    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    state = client.__getstate__()
    client.__setstate__(state)
    assert client._client is not None


# ---- Create / API call tests with mocking ----


@pytest.mark.asyncio
async def test_create_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test a basic non-streaming create call with mocked OpenAI client."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")

    # Mock the OpenAI client's chat.completions.create
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.function_call = None
    mock_choice.message.tool_calls = None
    mock_choice.message.content = "Hello from Avian!"
    mock_choice.message.model_extra = None
    mock_choice.logprobs = None

    mock_response = MagicMock()
    mock_response.model = "deepseek/deepseek-v3.2"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.model_dump.return_value = {"id": "test", "choices": [], "model": "deepseek/deepseek-v3.2"}

    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.create([UserMessage(content="Hello!", source="user")])

    assert isinstance(result, CreateResult)
    assert result.content == "Hello from Avian!"
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5


@pytest.mark.asyncio
async def test_create_with_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test create with function calling / tool calls."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")

    # Mock tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = '{"location": "Paris"}'

    mock_choice = MagicMock()
    mock_choice.finish_reason = "tool_calls"
    mock_choice.message.function_call = None
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_choice.message.content = None
    mock_choice.message.model_extra = None
    mock_choice.logprobs = None

    mock_response = MagicMock()
    mock_response.model = "deepseek/deepseek-v3.2"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 15
    mock_response.model_dump.return_value = {"id": "test", "choices": [], "model": "deepseek/deepseek-v3.2"}

    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    def get_weather(location: str) -> str:
        """Get the weather for a location."""
        return f"Sunny in {location}"

    tool = FunctionTool(get_weather, description="Get weather")

    result = await client.create(
        [UserMessage(content="What is the weather in Paris?", source="user")],
        tools=[tool],
    )

    assert isinstance(result, CreateResult)
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert result.content[0].name == "get_weather"
    assert result.content[0].id == "call_123"
    assert result.finish_reason == "function_calls"


@pytest.mark.asyncio
async def test_create_usage_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that usage is tracked correctly across calls."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")

    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.function_call = None
    mock_choice.message.tool_calls = None
    mock_choice.message.content = "Response"
    mock_choice.message.model_extra = None
    mock_choice.logprobs = None

    mock_response = MagicMock()
    mock_response.model = "deepseek/deepseek-v3.2"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.model_dump.return_value = {"id": "test", "choices": [], "model": "deepseek/deepseek-v3.2"}

    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await client.create([UserMessage(content="Hello!", source="user")])
    await client.create([UserMessage(content="Again!", source="user")])

    total = client.total_usage()
    assert total.prompt_tokens == 20
    assert total.completion_tokens == 10


@pytest.mark.asyncio
async def test_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that close calls the underlying client close."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    client._client.close = AsyncMock()

    await client.close()
    client._client.close.assert_called_once()


def test_remaining_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test remaining_tokens returns a reasonable value."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    remaining = client.remaining_tokens([UserMessage(content="Hello", source="user")])
    # Should be close to 164K minus a small number of tokens for the message
    assert remaining > 163_000
    assert remaining < 164_000


def test_count_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test count_tokens returns a positive value."""
    monkeypatch.setenv("AVIAN_API_KEY", "test-key")

    client = AvianChatCompletionClient(model="deepseek/deepseek-v3.2")
    count = client.count_tokens([UserMessage(content="Hello world", source="user")])
    assert count > 0


# ---- Component loading test ----


def test_component_type() -> None:
    assert AvianChatCompletionClient.component_type == "model"


def test_component_provider_override() -> None:
    assert AvianChatCompletionClient.component_provider_override == "autogen_ext.models.avian.AvianChatCompletionClient"
