#!/usr/bin/env python3
# pyright: reportPrivateUsage=false, reportIncompatibleMethodOverride=false, reportUnusedImport=false
"""
Test script to verify OpenAI agent built-in tools validation and configuration works correctly.
"""

import json
import os
from typing import Any, Dict, Final, List, Mapping, Type, Union
from unittest.mock import Mock

import pytest
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken, ComponentModel
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.agents.openai._openai_agent import OpenAIAgent, OpenAIAgentConfig
from openai import AsyncOpenAI
from pydantic import BaseModel


class TestOpenAIAgentBuiltinToolValidation:
    """Test class for OpenAI agent built-in tools validation."""

    @pytest.fixture
    def mock_client(self) -> AsyncOpenAI:
        """Create a mock OpenAI client for testing."""
        return AsyncOpenAI(api_key="test_key")

    def test_string_format_validation_success(self, mock_client: AsyncOpenAI) -> None:
        """Test that tools without required parameters work in string format."""
        # These should work (tools without required parameters)
        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="gpt-4",
            instructions="test",
            tools=["web_search_preview", "image_generation"],
        )
        # Test that the agent was created successfully without accessing protected attributes
        assert agent is not None
        assert agent.name == "test"

    def test_local_shell_model_validation_success(self, mock_client: AsyncOpenAI) -> None:
        """Test that local_shell works with codex-mini-latest model."""
        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="codex-mini-latest",
            instructions="test",
            tools=["local_shell"],
        )
        # Test that the agent was created successfully
        assert agent is not None
        assert agent.name == "test"

    def test_local_shell_model_validation_failure(self, mock_client: AsyncOpenAI) -> None:
        """Test that local_shell fails with non-codex-mini-latest models."""
        unsupported_models = ["gpt-4", "gpt-4o", "o3", "o4-mini", "gpt-3.5-turbo"]

        for model in unsupported_models:
            with pytest.raises(ValueError) as exc_info:
                OpenAIAgent(
                    name="test",
                    description="test",
                    client=mock_client,
                    model=model,
                    instructions="test",
                    tools=["local_shell"],
                )
            error_message = str(exc_info.value)
            assert "local_shell" in error_message
            assert "codex-mini-latest" in error_message
            assert "severe limitations" in error_message
            assert "LocalCommandLineCodeExecutor" in error_message
            # Test the specific alternative suggestion text
            assert "Consider using autogen_ext.tools.code_execution.PythonCodeExecutionTool" in error_message
            assert "shell execution instead" in error_message

    def test_string_format_validation_failures(self, mock_client: AsyncOpenAI) -> None:
        """Test that tools requiring parameters raise errors when used in string format."""
        tools_requiring_params = ["file_search", "code_interpreter", "computer_use_preview", "mcp"]

        for tool in tools_requiring_params:
            with pytest.raises(ValueError) as exc_info:
                OpenAIAgent(
                    name="test",
                    description="test",
                    client=mock_client,
                    model="gpt-4",
                    instructions="test",
                    tools=[tool],  # type: ignore
                )
            assert "requires specific parameters" in str(exc_info.value)
            assert "Use dict configuration instead" in str(exc_info.value)

    def test_dict_format_validation_success(self, mock_client: AsyncOpenAI) -> None:
        """Test that properly configured dict format works."""
        # Valid configurations
        valid_configs: List[Dict[str, Any]] = [
            {"type": "file_search", "vector_store_ids": ["vs_123", "vs_456"]},
            {"type": "computer_use_preview", "display_height": 1024, "display_width": 1280, "environment": "desktop"},
            {"type": "code_interpreter", "container": "python-3.11"},
            {"type": "mcp", "server_label": "test-server", "server_url": "http://localhost:3000"},
        ]

        for config in valid_configs:
            agent = OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=[config],  # type: ignore
            )
            # Test that the agent was created successfully without accessing protected attributes
            assert agent is not None
            assert agent.name == "test"

    def test_local_shell_dict_format_validation_success(self, mock_client: AsyncOpenAI) -> None:
        """Test that local_shell works in dict format with codex-mini-latest model."""
        config = {"type": "local_shell"}

        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="codex-mini-latest",
            instructions="test",
            tools=[config],  # type: ignore
        )
        # Test that the agent was created successfully
        assert agent is not None
        assert agent.name == "test"

    def test_local_shell_dict_format_validation_failure(self, mock_client: AsyncOpenAI) -> None:
        """Test that local_shell fails in dict format with non-codex-mini-latest models."""
        config = {"type": "local_shell"}
        unsupported_models = ["gpt-4", "gpt-4o", "o3", "o4-mini"]

        for model in unsupported_models:
            with pytest.raises(ValueError) as exc_info:
                OpenAIAgent(
                    name="test",
                    description="test",
                    client=mock_client,
                    model=model,
                    instructions="test",
                    tools=[config],  # type: ignore
                )
            error_message = str(exc_info.value)
            assert "local_shell" in error_message
            assert "codex-mini-latest" in error_message
            assert "severe limitations" in error_message
            assert "LocalCommandLineCodeExecutor" in error_message
            # Test the specific alternative suggestion text for dict format
            assert "Consider using autogen_ext.tools.code_execution.PythonCodeExecutionTool" in error_message
            assert "shell execution instead" in error_message

    def test_invalid_parameter_validation(self, mock_client: AsyncOpenAI) -> None:
        """Test that invalid parameter values are caught."""
        # Invalid configurations
        invalid_configs: List[Dict[str, Any]] = [
            {
                "type": "file_search",
                "vector_store_ids": [],  # Empty list should fail
                "expected_error": "file_search 'vector_store_ids' must be a non-empty list of strings",
            },
            {
                "type": "file_search",
                "vector_store_ids": ["", "valid"],  # Empty string in list should fail
                "expected_error": "file_search 'vector_store_ids' must contain non-empty strings",
            },
            {
                "type": "computer_use_preview",
                "display_height": -1,  # Negative should fail
                "display_width": 1280,
                "environment": "desktop",
                "expected_error": "computer_use_preview 'display_height' must be a positive integer",
            },
            {
                "type": "computer_use_preview",
                "display_height": 1024,
                "display_width": 0,  # Zero should fail
                "environment": "desktop",
                "expected_error": "computer_use_preview 'display_width' must be a positive integer",
            },
            {
                "type": "computer_use_preview",
                "display_height": 1024,
                "display_width": 1280,
                "environment": "",  # Empty string should fail
                "expected_error": "computer_use_preview 'environment' must be a non-empty string",
            },
            {
                "type": "mcp",
                "server_label": "",  # Empty string should fail
                "server_url": "http://localhost:3000",
                "expected_error": "mcp 'server_label' must be a non-empty string",
            },
            {
                "type": "mcp",
                "server_label": "valid-label",
                "server_url": "",  # Empty string should fail
                "expected_error": "mcp 'server_url' must be a non-empty string",
            },
            {
                "type": "code_interpreter",
                "container": "",  # Empty string should fail
                "expected_error": "code_interpreter 'container' must be a non-empty string",
            },
        ]

        for config in invalid_configs:
            expected_error = str(config.pop("expected_error"))
            with pytest.raises(ValueError) as exc_info:
                OpenAIAgent(
                    name="test",
                    description="test",
                    client=mock_client,
                    model="gpt-4",
                    instructions="test",
                    tools=[config],  # type: ignore
                )
            assert expected_error in str(exc_info.value)

    def test_optional_parameters_validation(self, mock_client: AsyncOpenAI) -> None:
        """Test that optional parameters are correctly validated."""
        valid_optional_configs: List[Dict[str, Any]] = [
            {
                "type": "file_search",
                "vector_store_ids": ["vs_123"],
                "max_num_results": 5,
                "ranking_options": {"ranker": "default_2024_08_21", "score_threshold": 0.5},
                "filters": {"type": "eq", "key": "document_type", "value": "pdf"},
            },
            {
                "type": "web_search_preview",
                "search_context_size": 5,
                "user_location": "Seattle, WA",  # String format
            },
            {
                "type": "web_search_preview",
                "search_context_size": 10,
                "user_location": {  # Dictionary format
                    "type": "approximate",
                    "country": "US",
                    "region": "WA",
                    "city": "Seattle",
                },
            },
            {
                "type": "mcp",
                "server_label": "test",
                "server_url": "http://localhost:3000",
                "allowed_tools": ["tool1", "tool2"],
                "headers": {"Authorization": "Bearer token"},
                "require_approval": True,
            },
            {
                "type": "image_generation",
                "background": "white",
                "input_image_mask": "mask_data",
            },
        ]

        for config in valid_optional_configs:
            agent = OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=[config],  # type: ignore
            )
            assert agent is not None

        # Test invalid optional parameter values
        invalid_optional_configs: List[Dict[str, Any]] = [
            {
                "type": "file_search",
                "vector_store_ids": ["vs_123"],
                "max_num_results": -1,  # Negative should fail
                "expected_error": "file_search 'max_num_results' must be a positive integer",
            },
            {
                "type": "web_search_preview",
                "search_context_size": 0,  # Zero should fail
                "expected_error": "web_search_preview 'search_context_size' must be a positive integer",
            },
            {
                "type": "web_search_preview",
                "user_location": "",  # Empty string should fail
                "expected_error": (
                    "web_search_preview 'user_location' must be a non-empty string when using string format"
                ),
            },
            {
                "type": "web_search_preview",
                "user_location": {"country": "US"},  # Missing required 'type' field
                "expected_error": "web_search_preview 'user_location' dictionary must include 'type' field",
            },
            {
                "type": "web_search_preview",
                "user_location": {"type": "invalid"},  # Invalid type value
                "expected_error": "web_search_preview 'user_location' type must be 'approximate' or 'exact'",
            },
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate", "country": ""},  # Empty country
                "expected_error": "web_search_preview 'user_location' country must be a non-empty string",
            },
            {
                "type": "mcp",
                "server_label": "test",
                "server_url": "http://localhost:3000",
                "allowed_tools": ["valid", 123],  # Invalid type in list
                "expected_error": "mcp 'allowed_tools' must contain only strings",
            },
        ]

        for config in invalid_optional_configs:
            expected_error = config.pop("expected_error")
            with pytest.raises(ValueError) as exc_info:
                OpenAIAgent(
                    name="test",
                    description="test",
                    client=mock_client,
                    model="gpt-4",
                    instructions="test",
                    tools=[config],  # type: ignore
                )
            assert expected_error in str(exc_info.value)

    def test_mixed_tools_configuration(self, mock_client: AsyncOpenAI) -> None:
        """Test that mixed tool configurations work correctly."""
        from autogen_core.tools import Tool

        # Create a simple mock tool
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.schema = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
        }

        # Mix of string format, dict format, and custom Tool
        mixed_tools: List[Union[str, Dict[str, Any], Mock]] = [
            "web_search_preview",  # String format
            {"type": "file_search", "vector_store_ids": ["vs_123"]},  # Dict format
            mock_tool,  # Custom Tool
        ]

        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="gpt-4",
            instructions="test",
            tools=mixed_tools,  # type: ignore
        )

        # Test that the agent was created successfully without accessing protected attributes
        assert agent is not None
        assert agent.name == "test"

    def test_mixed_tools_with_local_shell(self, mock_client: AsyncOpenAI) -> None:
        """Test mixed tools configuration that includes local_shell with appropriate model."""
        from autogen_core.tools import Tool

        # Create a simple mock tool
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.schema = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
        }

        # Mix including local_shell
        mixed_tools: List[Union[str, Dict[str, Any], Mock]] = [
            "local_shell",  # String format - only works with codex-mini-latest
            {"type": "local_shell"},  # Dict format - also only works with codex-mini-latest
            mock_tool,  # Custom Tool
        ]

        # Should work with codex-mini-latest
        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="codex-mini-latest",
            instructions="test",
            tools=mixed_tools,  # type: ignore
        )

        # Test that the agent was created successfully
        assert agent is not None
        assert agent.name == "test"

    def test_unsupported_tool_type(self, mock_client: AsyncOpenAI) -> None:
        """Test that unsupported tool types raise appropriate errors."""
        with pytest.raises(ValueError) as exc_info:
            OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=["unsupported_tool"],  # type: ignore
            )
        assert "Unsupported built-in tool type: unsupported_tool" in str(exc_info.value)

    def test_invalid_tool_configuration_format(self, mock_client: AsyncOpenAI) -> None:
        """Test that invalid tool configuration formats raise errors."""
        # Test dict without 'type' field - this goes to the final else clause
        with pytest.raises(ValueError) as exc_info:
            OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=[{"invalid": "config"}],  # type: ignore
            )
        assert "Unsupported tool type:" in str(exc_info.value)

        # Test dict with 'type' field but invalid type value
        with pytest.raises(ValueError) as exc_info:
            OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=[{"type": "invalid_tool_type"}],  # type: ignore
            )
        assert "Unsupported built-in tool type: invalid_tool_type" in str(exc_info.value)

        # Test unsupported tool type (not string, dict, or Tool)
        with pytest.raises(ValueError) as exc_info:
            OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="gpt-4",
                instructions="test",
                tools=[123],  # type: ignore  # Invalid type
            )
        assert "Unsupported tool type:" in str(exc_info.value)

    def test_local_shell_type_validation(self, mock_client: AsyncOpenAI) -> None:
        """Test that LocalShellToolConfig type validation works correctly."""
        # Test valid LocalShellToolConfig structure
        valid_config = {"type": "local_shell"}

        # Should work with correct model
        agent = OpenAIAgent(
            name="test",
            description="test",
            client=mock_client,
            model="codex-mini-latest",
            instructions="test",
            tools=[valid_config],  # type: ignore
        )
        assert agent is not None

        # Test that invalid type value is caught by our validation
        invalid_config = {"type": "invalid_shell_type"}
        with pytest.raises(ValueError) as exc_info:
            OpenAIAgent(
                name="test",
                description="test",
                client=mock_client,
                model="codex-mini-latest",
                instructions="test",
                tools=[invalid_config],  # type: ignore
            )
        assert "Unsupported built-in tool type: invalid_shell_type" in str(exc_info.value)

    # Configuration serialization/deserialization tests
    def test_config_serialize_builtin_tools(self, mock_client: AsyncOpenAI) -> None:
        """Test serialization of built-in tools to config."""
        agent = OpenAIAgent(
            name="config_test_agent",
            description="Agent for config testing",
            client=mock_client,
            model="gpt-4",
            instructions="You are a helpful assistant.",
            tools=[
                {"type": "web_search_preview", "search_context_size": 5},
                {"type": "file_search", "vector_store_ids": ["vs_123"]},
            ],
        )

        # Serialize to config
        config = agent._to_config()

        # Verify config contains tools
        assert config.tools is not None
        assert len(config.tools) == 2

        # Check tools are preserved as dict format
        web_search_tool = next(t for t in config.tools if isinstance(t, dict) and t["type"] == "web_search_preview")
        file_search_tool = next(t for t in config.tools if isinstance(t, dict) and t["type"] == "file_search")

        # "search_context_size" is optional in TypedDict; use .get for safe access
        assert web_search_tool.get("search_context_size") == 5
        assert file_search_tool["vector_store_ids"] == ["vs_123"]

    def test_config_deserialize_builtin_tools(self, mock_client: AsyncOpenAI) -> None:
        """Test deserialization of built-in tools from config."""
        config = OpenAIAgentConfig(
            name="deserialize_test_agent",
            description="Agent for deserialization testing",
            model="gpt-4",
            instructions="You are a helpful assistant.",
            tools=[
                {"type": "web_search_preview"},
                {"type": "mcp", "server_label": "test-server", "server_url": "http://localhost:3000"},
            ],
        )

        # Deserialize from config
        agent = OpenAIAgent._from_config(config)

        # Verify agent has tools
        assert len(agent._tools) == 2

        web_search_tool = next(t for t in agent._tools if t["type"] == "web_search_preview")
        mcp_tool = next(t for t in agent._tools if t["type"] == "mcp")

        assert web_search_tool is not None
        assert mcp_tool["server_label"] == "test-server"
        assert mcp_tool["server_url"] == "http://localhost:3000"

    def test_config_round_trip_builtin_tools(self, mock_client: AsyncOpenAI) -> None:
        """Test round-trip serialization/deserialization of built-in tools."""
        original_tools = [
            {"type": "web_search_preview", "search_context_size": 3},
            {"type": "file_search", "vector_store_ids": ["vs_abc"], "max_num_results": 5},
        ]

        # Create original agent
        original_agent = OpenAIAgent(
            name="round_trip_agent",
            description="Round trip test agent",
            client=mock_client,
            model="gpt-4",
            instructions="You are a helpful assistant.",
            tools=original_tools,  # type: ignore
        )

        # Serialize to config and back
        config = original_agent._to_config()
        reconstructed_agent = OpenAIAgent._from_config(config)

        # Verify agent properties preserved
        assert reconstructed_agent.name == original_agent.name
        assert reconstructed_agent.description == original_agent.description
        assert reconstructed_agent._model == original_agent._model

        # Verify tools preserved
        assert len(reconstructed_agent._tools) == 2

        web_search_tool = next(t for t in reconstructed_agent._tools if t["type"] == "web_search_preview")
        file_search_tool = next(t for t in reconstructed_agent._tools if t["type"] == "file_search")

        assert web_search_tool["search_context_size"] == 3
        assert file_search_tool["vector_store_ids"] == ["vs_abc"]
        assert file_search_tool["max_num_results"] == 5

    def test_config_json_serialization_builtin_tools(self, mock_client: AsyncOpenAI) -> None:
        """Test that config with built-in tools can be JSON serialized/deserialized."""
        agent = OpenAIAgent(
            name="json_test_agent",
            description="JSON test agent",
            client=mock_client,
            model="gpt-4",
            instructions="You are a helpful assistant.",
            tools=[
                {"type": "web_search_preview", "search_context_size": 7},
                {"type": "image_generation", "background": "white"},
            ],
        )

        # Serialize to config and JSON
        config = agent._to_config()
        config_dict = config.model_dump()
        json_str = json.dumps(config_dict, indent=2)

        # Parse JSON and recreate config
        parsed_dict = json.loads(json_str)
        restored_config = OpenAIAgentConfig.model_validate(parsed_dict)

        # Verify config preserved
        assert restored_config.name == "json_test_agent"
        assert restored_config.tools is not None
        assert len(restored_config.tools) == 2

        # Create agent from restored config
        restored_agent = OpenAIAgent._from_config(restored_config)
        assert restored_agent.name == "json_test_agent"
        assert len(restored_agent._tools) == 2

    def test_config_mixed_tools_serialization(self, mock_client: AsyncOpenAI) -> None:
        """Test serialization of mixed custom and built-in tools."""

        from autogen_core.tools import ToolSchema

        class MockCustomTool(Tool):
            @property
            def name(self) -> str:
                return "custom_test_tool"

            @property
            def description(self) -> str:
                return "A custom test tool"

            @property
            def schema(self) -> "ToolSchema":  # type: ignore[name-defined]
                return {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                        "required": ["input"],
                    },
                }

            def args_type(self) -> "Type[BaseModel]":  # type: ignore[name-defined]
                from pydantic import BaseModel

                class _Args(BaseModel):
                    input: str

                return _Args

            def return_type(self) -> "Type[BaseModel]":  # type: ignore[name-defined]
                from pydantic import BaseModel

                class _Return(BaseModel):
                    result: str

                return _Return

            def state_type(self) -> None:  # type: ignore[override]
                return None

            async def save_state_json(self) -> Dict[str, Any]:  # type: ignore[override]
                return {}

            async def load_state_json(self, state: Mapping[str, Any]) -> None:  # type: ignore[override]
                return None

            async def run_json(
                self,
                args: Mapping[str, Any],
                cancellation_token: CancellationToken,
                call_id: str | None = None,
            ) -> Dict[str, Any]:
                return {"result": "test"}

            def return_value_as_string(self, value: Dict[str, Any]) -> str:
                return str(value)

        custom_tool = MockCustomTool()
        tools = [
            custom_tool,  # Custom tool
            {"type": "web_search_preview"},  # Built-in tool
        ]

        agent = OpenAIAgent(
            name="mixed_tools_agent",
            description="Mixed tools agent",
            client=mock_client,
            model="gpt-4",
            instructions="You are a helpful assistant.",
            tools=tools,  # type: ignore
        )

        # Serialize to config
        config = agent._to_config()

        # Verify both types of tools are present
        assert config.tools is not None
        assert len(config.tools) == 2

        component_models = [t for t in config.tools if isinstance(t, ComponentModel)]
        builtin_tools = [t for t in config.tools if isinstance(t, dict)]

        assert len(component_models) == 1  # Custom tool
        assert len(builtin_tools) == 1  # Built-in tool

        # Verify custom tool config
        custom_tool_config = component_models[0]
        assert custom_tool_config.config.get("name") == "custom_test_tool"

        # Verify built-in tool config
        builtin_tool_config = builtin_tools[0]
        assert builtin_tool_config["type"] == "web_search_preview"


# Live API Integration Tests

# These tests make a real call to the OpenAI Responses API. They are executed
# only when an API key is available in the environment so that CI pipelines
# without secret keys (or local developers without a key) do not incur
# failures or unexpected costs.

_OPENAI_API_KEY_ENV: Final[str] = "OPENAI_API_KEY"


@pytest.mark.skipif(
    not os.getenv(_OPENAI_API_KEY_ENV),
    reason="OpenAI API key not available; skipping live API integration tests.",
)
@pytest.mark.asyncio
async def test_openai_agent_live_simple() -> None:  # noqa: D103
    cancellation_token = CancellationToken()
    client = AsyncOpenAI()  # API key picked up from env

    agent = OpenAIAgent(
        name="integration_test_agent",
        description="Agent used for live API integration testing",
        client=client,
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        instructions="You are a concise assistant. Reply briefly.",
    )

    response = await agent.on_messages(
        [TextMessage(source="user", content="Say hello briefly.")],
        cancellation_token,
    )

    # Basic sanity checks on the response (cast to TextMessage for typing)
    from typing import cast

    reply_msg = cast(TextMessage, response.chat_message)
    reply: str = reply_msg.content.strip()
    assert reply != ""
    assert "hello" in reply.lower()


@pytest.mark.skipif(
    not os.getenv(_OPENAI_API_KEY_ENV),
    reason="OpenAI API key not available; skipping live API integration tests.",
)
@pytest.mark.asyncio
async def test_openai_agent_live_with_builtin_tool() -> None:  # noqa: D103
    """Live test that ensures at least one built-in tool schema reaches the API without error."""
    cancellation_token = CancellationToken()
    client = AsyncOpenAI()  # API key picked up from env

    # Use a simple built-in tool that requires no parameters so the test is stable.
    agent = OpenAIAgent(
        name="integration_test_agent_builtin",
        description="Agent used for live API integration testing with built-in tools",
        client=client,
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        instructions="You are a concise assistant. Reply briefly.",
        tools=["web_search_preview"],
    )

    response = await agent.on_messages(
        [TextMessage(source="user", content="What is the capital of France?")],
        cancellation_token,
    )

    from typing import cast

    reply_msg = cast(TextMessage, response.chat_message)
    reply: str = reply_msg.content.strip()
    assert reply != ""
    # Very loose assertion – just ensure the model responded sensibly
    assert "paris" in reply.lower()
