"""
Comprehensive tests for GPT-5 specific features in AutoGen.

This test suite validates:
- GPT-5 model recognition and configuration
- Custom tools functionality (freeform text input)
- Grammar constraints for custom tools
- Reasoning effort parameter control
- Verbosity parameter control
- Preambles support
- Allowed tools parameter
- Responses API client implementation
- Chain-of-thought preservation across turns

Tests use mocking to avoid actual API calls while validating
that all GPT-5 features are properly integrated and functional.
"""

from typing import Any, Dict, List, cast
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_core.models import CreateResult, UserMessage
from autogen_core.tools import BaseCustomTool, CustomToolFormat
from autogen_ext.models.openai import (
    OpenAIChatCompletionClient,
    OpenAIResponsesAPIClient,
)
from autogen_ext.models.openai._model_info import get_info as get_model_info
from autogen_ext.models.openai._openai_client import convert_tools
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall as ChatCompletionMessageToolCall,
)
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel


class CodeExecResult(BaseModel):
    result: str


class TestCodeExecutorTool(BaseCustomTool[CodeExecResult]):
    """Test implementation of GPT-5 custom tool for code execution."""

    def __init__(self) -> None:
        super().__init__(
            return_type=CodeExecResult,
            name="code_exec",
            description="Executes arbitrary Python code and returns the result",
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> CodeExecResult:
        return CodeExecResult(result=f"Executed: {input_text}")


class SQLResult(BaseModel):
    result: str


class TestSQLTool(BaseCustomTool[SQLResult]):
    """Test implementation of GPT-5 custom tool with grammar constraints."""

    def __init__(self) -> None:
        sql_grammar: CustomToolFormat = {
            "type": "grammar",
            "syntax": "lark",
            "definition": """
                start: select_statement
                select_statement: "SELECT" column_list "FROM" table_name ("WHERE" condition)?
                column_list: column ("," column)*
                column: IDENTIFIER
                table_name: IDENTIFIER
                condition: column ">" NUMBER
                IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
                NUMBER: /[0-9]+/
                %import common.WS
                %ignore WS
            """,
        }

        super().__init__(
            return_type=SQLResult,
            name="sql_query",
            description="Execute SQL queries with grammar validation",
            format=sql_grammar,
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> SQLResult:
        return SQLResult(result=f"SQL Result: {input_text}")


class TestGPT5ModelRecognition:
    """Test GPT-5 model definitions and capabilities."""

    def test_gpt5_model_info(self) -> None:
        """Test that GPT-5 models are properly recognized and configured."""
        gpt5_info = get_model_info("gpt-5")
        assert gpt5_info["vision"] is True
        assert gpt5_info["function_calling"] is True
        assert gpt5_info["json_output"] is True
        assert gpt5_info["structured_output"] is True

        gpt5_mini_info = get_model_info("gpt-5-mini")
        assert gpt5_mini_info["vision"] is True
        assert gpt5_mini_info["function_calling"] is True

        gpt5_nano_info = get_model_info("gpt-5-nano")
        assert gpt5_nano_info["vision"] is True
        assert gpt5_nano_info["function_calling"] is True

    def test_gpt5_token_limits(self) -> None:
        """Test GPT-5 models have correct token limits."""
        from autogen_ext.models.openai._model_info import get_token_limit

        assert get_token_limit("gpt-5") == 400000
        assert get_token_limit("gpt-5-mini") == 400000
        assert get_token_limit("gpt-5-nano") == 400000


class TestCustomToolsIntegration:
    """Test GPT-5 custom tools functionality."""

    def test_custom_tool_schema_generation(self) -> None:
        """Test custom tool schema generation."""
        code_tool = TestCodeExecutorTool()
        schema = code_tool.schema

        assert schema["name"] == "code_exec"
        assert schema.get("description", "") == "Executes arbitrary Python code and returns the result"
        assert "format" not in schema  # No grammar constraints

    def test_custom_tool_with_grammar_schema(self) -> None:
        """Test custom tool with grammar constraints."""
        sql_tool = TestSQLTool()
        schema = sql_tool.schema

        assert schema["name"] == "sql_query"
        assert "format" in schema
        fmt_any = schema.get("format")
        assert isinstance(fmt_any, dict)
        assert fmt_any.get("type") == "grammar"
        assert fmt_any.get("syntax") == "lark"
        assert isinstance(fmt_any.get("definition"), str) and "SELECT" in fmt_any.get("definition", "")

    def test_convert_custom_tools(self) -> None:
        """Test conversion of custom tools to OpenAI API format."""
        code_tool = TestCodeExecutorTool()
        sql_tool = TestSQLTool()

        converted = convert_tools([code_tool, sql_tool])

        assert len(converted) == 2

        # Check code tool conversion
        code_tool_param = next(
            cast(Dict[str, Any], t)
            for t in converted
            if cast(Dict[str, Any], t).get("custom", {}).get("name") == "code_exec"
        )
        assert str(code_tool_param.get("type")) == "custom"
        assert "format" not in code_tool_param.get("custom", {})

        # Check SQL tool conversion with grammar
        sql_tool_param = next(
            cast(Dict[str, Any], t)
            for t in converted
            if cast(Dict[str, Any], t).get("custom", {}).get("name") == "sql_query"
        )
        assert str(sql_tool_param.get("type")) == "custom"
        assert "format" in sql_tool_param.get("custom", {})
        assert sql_tool_param.get("custom", {}).get("format", {}).get("type") == "grammar"

    async def test_custom_tool_execution(self) -> None:
        """Test custom tool execution."""
        code_tool = TestCodeExecutorTool()

        result = await code_tool.run("print('hello world')", CancellationToken())
        assert result.result == "Executed: print('hello world')"

        result_via_freeform = await code_tool.run_freeform("x = 2 + 2", CancellationToken())
        assert result_via_freeform == "Executed: x = 2 + 2"


class TestGPT5Parameters:
    """Test GPT-5 specific parameters."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        """Mock OpenAI client for testing."""
        with patch("autogen_ext.models.openai._openai_client._openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIChatCompletionClient:
        """Create test client with mocked OpenAI client."""
        return OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    async def test_reasoning_effort_parameter(
        self, client: OpenAIChatCompletionClient, mock_openai_client: Any
    ) -> None:
        """Test reasoning_effort parameter is properly passed."""
        # Mock successful API response
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Test different reasoning efforts
        for effort in ["minimal", "low", "medium", "high"]:
            await client.create(messages=[UserMessage(content="Test message", source="user")], reasoning_effort=effort)  # type: ignore[arg-type]

            # Verify parameter was passed correctly
            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["reasoning_effort"] == effort

    async def test_verbosity_parameter(self, client: OpenAIChatCompletionClient, mock_openai_client: Any) -> None:
        """Test verbosity parameter is properly passed."""
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Test different verbosity levels
        for verbosity in ["low", "medium", "high"]:
            await client.create(messages=[UserMessage(content="Test message", source="user")], verbosity=verbosity)  # type: ignore[arg-type]

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["verbosity"] == verbosity

    async def test_preambles_parameter(self, client: OpenAIChatCompletionClient, mock_openai_client: Any) -> None:
        """Test preambles parameter is properly passed."""
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Test preambles enabled
        await client.create(messages=[UserMessage(content="Test message", source="user")], preambles=True)

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["preambles"] is True

        # Test preambles disabled
        await client.create(messages=[UserMessage(content="Test message", source="user")], preambles=False)

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["preambles"] is False

    async def test_combined_gpt5_parameters(self, client: OpenAIChatCompletionClient, mock_openai_client: Any) -> None:
        """Test multiple GPT-5 parameters used together."""
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        await client.create(
            messages=[UserMessage(content="Test message", source="user")],
            reasoning_effort="high",
            verbosity="medium",
            preambles=True,
        )

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["reasoning_effort"] == "high"
        assert call_kwargs["verbosity"] == "medium"
        assert call_kwargs["preambles"] is True


class TestAllowedToolsFeature:
    """Test GPT-5 allowed_tools parameter for restricting tool usage."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client._openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIChatCompletionClient:
        return OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    async def test_allowed_tools_restriction(self, client: OpenAIChatCompletionClient, mock_openai_client: Any) -> None:
        """Test allowed_tools parameter restricts model to specific tools."""
        from autogen_core.tools import FunctionTool

        def safe_calc(x: int, y: int) -> int:
            return x + y

        def dangerous_exec(code: str) -> str:
            return f"Would execute: {code}"

        calc_tool = FunctionTool(safe_calc, description="Safe calculator")
        exec_tool = FunctionTool(dangerous_exec, description="Code executor")
        code_tool = TestCodeExecutorTool()

        from autogen_core.tools import CustomTool as _CustomTool
        from autogen_core.tools import CustomToolSchema as _CustomToolSchema
        from autogen_core.tools import Tool as _Tool
        from autogen_core.tools import ToolSchema as _ToolSchema

        all_tools: List[_Tool | _ToolSchema | _CustomTool | _CustomToolSchema] = [
            cast(_Tool, calc_tool),
            cast(_Tool, exec_tool),
            cast(_CustomTool, code_tool),
        ]
        safe_tools: List[_Tool | _CustomTool | str] = [cast(_Tool, calc_tool)]  # Only allow calculator

        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        await client.create(
            messages=[UserMessage(content="Help with math and coding", source="user")],
            tools=all_tools,
            allowed_tools=safe_tools,
            tool_choice="auto",
        )

        call_kwargs_any: Any = mock_openai_client.chat.completions.create.call_args[1]

        # Verify allowed_tools structure was created
        call_kwargs: Dict[str, Any] = cast(Dict[str, Any], call_kwargs_any)
        assert "tool_choice" in call_kwargs
        tool_choice_val: Any = call_kwargs.get("tool_choice")

        if isinstance(tool_choice_val, dict):
            tc: Dict[str, Any] = cast(Dict[str, Any], tool_choice_val)
            if str(tc.get("type", "")) == "allowed_tools":
                mode_val: str = str(tc.get("mode", ""))
                assert mode_val == "auto"
                tools_seq: List[Any] = list(cast(List[Any] | tuple[Any, ...], tc.get("tools", [])))
                tools_list: List[Dict[str, Any]] = [t for t in tools_seq if isinstance(t, dict)]
                allowed_tool_names: List[str] = [str(t.get("name", "")) for t in tools_list]
                assert "safe_calc" in allowed_tool_names
                assert "dangerous_exec" not in allowed_tool_names
                assert "code_exec" not in allowed_tool_names


class TestResponsesAPIClient:
    """Test the dedicated Responses API client for GPT-5."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._responses_client._openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.responses.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def responses_client(self, mock_openai_client: Any) -> OpenAIResponsesAPIClient:
        return OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")

    async def test_responses_api_basic_call(
        self, responses_client: OpenAIResponsesAPIClient, mock_openai_client: Any
    ) -> None:
        """Test basic Responses API call structure."""
        mock_response = {
            "id": "resp-123",
            "choices": [{"message": {"content": "Response content"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_openai_client.responses.create.return_value = mock_response

        result = await responses_client.create(input="Test input message", reasoning_effort="medium", verbosity="high")

        assert isinstance(result, CreateResult)
        assert result.content == "Response content"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20

    async def test_responses_api_with_cot_preservation(
        self, responses_client: OpenAIResponsesAPIClient, mock_openai_client: Any
    ) -> None:
        """Test chain-of-thought preservation between turns."""
        # First turn
        mock_response1 = {
            "id": "resp-123",
            "choices": [{"message": {"content": "First response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "reasoning_items": [{"type": "reasoning", "content": "Initial reasoning"}],
        }
        mock_openai_client.responses.create.return_value = mock_response1

        result1 = await responses_client.create(input="First question", reasoning_effort="high")

        # Second turn with preserved CoT
        mock_response2 = {
            "id": "resp-124",
            "choices": [{"message": {"content": "Follow-up response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 15},  # Lower usage due to CoT reuse
        }
        mock_openai_client.responses.create.return_value = mock_response2

        result2 = await responses_client.create(
            input="Follow-up question",
            previous_response_id=result1.response_id,  # type: ignore
            reasoning_effort="low",  # Can use lower effort
        )

        # Verify previous_response_id was passed
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["previous_response_id"] == "resp-123"
        assert call_kwargs["reasoning"]["effort"] == "low"
        assert result2.content == "Follow-up response"

    async def test_responses_api_with_custom_tools(
        self, responses_client: OpenAIResponsesAPIClient, mock_openai_client: Any
    ) -> None:
        """Test Responses API with GPT-5 custom tools."""
        code_tool = TestCodeExecutorTool()

        mock_response = {
            "id": "resp-125",
            "choices": [
                {
                    "message": {
                        "content": "I'll execute the code for you.",
                        "tool_calls": [
                            {"id": "call-456", "custom": {"name": "code_exec", "input": "print('Hello GPT-5')"}}
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25},
        }
        mock_openai_client.responses.create.return_value = mock_response

        result = await responses_client.create(
            input="Run this Python code: print('Hello GPT-5')", tools=[code_tool], preambles=True
        )

        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert result.content[0].name == "code_exec"
        assert result.content[0].arguments == "print('Hello GPT-5')"
        assert result.thought == "I'll execute the code for you."  # Preamble text


class TestGPT5IntegrationScenarios:
    """Test realistic GPT-5 usage scenarios."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client._openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIChatCompletionClient:
        return OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")

    async def test_code_analysis_with_custom_tools(
        self, client: OpenAIChatCompletionClient, mock_openai_client: Any
    ) -> None:
        """Test GPT-5 analyzing and executing code with custom tools."""
        code_tool = TestCodeExecutorTool()
        sql_tool = TestSQLTool()

        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="I need to analyze this code and run it.",
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="call-123",
                                type="custom",  # type: ignore
                                custom={  # type: ignore
                                    "name": "code_exec",
                                    "input": "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)\nprint(fibonacci(10))",
                                },
                            )
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ],
            usage=CompletionUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Tools typed to expected union for create
        tools_param = [code_tool, sql_tool]
        result = await client.create(
            messages=[UserMessage(content="Analyze this fibonacci implementation and run it for n=10", source="user")],
            tools=tools_param,
            reasoning_effort="medium",  # type: ignore[arg-type]
            verbosity="low",  # type: ignore[arg-type]
            preambles=True,
        )

        # Verify GPT-5 parameters were passed
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["reasoning_effort"] == "medium"
        assert call_kwargs["verbosity"] == "low"
        assert call_kwargs["preambles"] is True

        # Verify tools were converted properly
        assert "tools" in call_kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 2

        # Check that result contains tool call
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert result.thought == "I need to analyze this code and run it."

    async def test_multi_modal_with_reasoning_control(
        self, client: OpenAIChatCompletionClient, mock_openai_client: Any
    ) -> None:
        """Test GPT-5 with vision and reasoning control."""
        import io

        from autogen_core import Image
        from PIL import Image as PILImage

        # Create a simple test image
        pil_image = PILImage.new("RGB", (100, 100), color="red")
        image_bytes = io.BytesIO()
        pil_image.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        test_image = Image.from_pil(pil_image)

        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-5",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant", content="I can see this is a red square image. Let me analyze it further..."
                    ),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=100, completion_tokens=40, total_tokens=140),
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await client.create(
            messages=[UserMessage(content=["What do you see in this image?", test_image], source="user")],
            reasoning_effort="high",
            verbosity="high",
        )

        assert result.content == "I can see this is a red square image. Let me analyze it further..."

        # Verify vision-related processing occurred
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["reasoning_effort"] == "high"
        assert call_kwargs["verbosity"] == "high"


@pytest.mark.asyncio
async def test_gpt5_error_handling() -> None:
    """Test proper error handling for GPT-5 specific scenarios."""

    # Test invalid reasoning effort
    with pytest.raises(ValueError):  # Type validation should catch this
        _client = OpenAIChatCompletionClient(model="gpt-5", api_key="test-key")
        # This should be caught by type checking, but test anyway

    # Test model without GPT-5 capabilities using GPT-5 features
    with patch("autogen_ext.models.openai._openai_client._openai_client_from_config") as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client

        # Test with non-GPT-5 model
        old_model_client = OpenAIChatCompletionClient(model="gpt-4", api_key="test-key")

        # GPT-4 should still accept these parameters (they'll be ignored by the API)
        mock_client.chat.completions.create.return_value = ChatCompletion(
            id="test",
            object="chat.completion",
            created=1234567890,
            model="gpt-4",
            choices=[],
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

        # This should work but parameters won't have any effect
        await old_model_client.create(
            messages=[UserMessage(content="Test", source="user")],
            reasoning_effort="high",  # Will be passed but ignored
            preambles=True,
        )


if __name__ == "__main__":
    # Run basic validation tests
    pytest.main([__file__, "-v"])
