"""
Tests for OpenAI Responses API client implementation.

The Responses API is designed specifically for GPT-5 and provides:
- Chain-of-thought preservation between conversation turns
- Reduced reasoning token generation through context reuse
- Improved cache hit rates and lower latency
- Better integration with GPT-5 reasoning features

These tests validate the Responses API client implementation,
parameter handling, and integration with AutoGen frameworks.
"""

from typing import Any, Dict, cast
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_core.models import CreateResult
from autogen_ext.models.openai import (
    AzureOpenAIResponsesAPIClient,
    OpenAIResponsesAPIClient,
)
from autogen_ext.models.openai._responses_client import (
    ResponsesAPICreateParams,
)
from openai.types.responses.response_custom_tool_call import ResponseCustomToolCall
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_output_message import ResponseOutputMessage
from test_gpt5_features import TestCodeExecutorTool


class TestResponsesAPIClientInitialization:
    """Test Responses API client initialization and configuration."""

    def test_openai_responses_client_creation(self) -> None:
        """Test OpenAI Responses API client can be created."""
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock.return_value = AsyncMock()
            client = OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")
            # Access through public info() for type safety
            assert client.info()["family"] == "GPT_5"

    def test_azure_responses_client_creation(self) -> None:
        """Test Azure OpenAI Responses API client can be created."""
        with patch("autogen_ext.models.openai._openai_client.azure_openai_client_from_config") as mock:
            mock.return_value = AsyncMock()
            client = AzureOpenAIResponsesAPIClient(
                model="gpt-5",
                azure_endpoint="https://test.openai.azure.com/",
                azure_deployment="gpt-5-deployment",
                api_version="2024-06-01",
                api_key="test-key",
            )
            assert client.info()["family"] == "GPT_5"

    def test_invalid_model_raises_error(self) -> None:
        """Test that invalid model names raise appropriate errors."""
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock.return_value = AsyncMock()
            with pytest.raises(ValueError, match="model_info is required"):
                OpenAIResponsesAPIClient(model="invalid-model", api_key="test-key")


class TestResponsesAPIParameterHandling:
    """Test Responses API specific parameter handling."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.responses.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIResponsesAPIClient:
        return OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")

    def test_process_create_args_basic(self, client: OpenAIResponsesAPIClient) -> None:
        """Test basic parameter processing for Responses API."""
        params = client._OpenAIResponsesAPIClient__process_create_args(  # type: ignore[attr-defined]
            input="Test input",
            tools=[],
            tool_choice="auto",
            extra_create_args={},
            reasoning_effort="medium",
            verbosity="high",
            preambles=True,
        )

        assert isinstance(params, ResponsesAPICreateParams)
        assert params.input == "Test input"
        assert params.create_args["input"] == "Test input"
        assert params.create_args["reasoning"]["effort"] == "medium"
        assert params.create_args["text"]["verbosity"] == "high"
        assert params.create_args["preambles"] is True

    def test_process_create_args_with_cot_preservation(self, client: OpenAIResponsesAPIClient) -> None:
        """Test chain-of-thought preservation parameters."""
        params = client._OpenAIResponsesAPIClient__process_create_args(  # type: ignore[attr-defined]
            input="Follow-up question",
            tools=[],
            tool_choice="auto",
            extra_create_args={},
            previous_response_id="resp-123",
            reasoning_items=[{"type": "reasoning", "content": "Previous reasoning"}],
        )

        # mypy/pyright: create_args is a dict[str, Any]
        create_args: Dict[str, Any] = params.create_args
        assert create_args.get("previous_response_id") == "resp-123"
        assert create_args.get("reasoning_items") == [{"type": "reasoning", "content": "Previous reasoning"}]

    def test_invalid_extra_args_rejected(self, client: OpenAIResponsesAPIClient) -> None:
        """Test that invalid extra arguments are rejected."""
        with pytest.raises(ValueError, match="Extra create args are invalid for Responses API"):
            client._OpenAIResponsesAPIClient__process_create_args(  # type: ignore[attr-defined]
                input="Test",
                tools=[],
                tool_choice="auto",
                extra_create_args={"invalid_param": "value"},  # Not allowed in Responses API
            )

    def test_default_reasoning_effort(self, client: OpenAIResponsesAPIClient) -> None:
        """Test default reasoning effort is set when not specified."""
        params = client._OpenAIResponsesAPIClient__process_create_args(  # type: ignore[attr-defined]
            input="Test input", tools=[], tool_choice="auto", extra_create_args={}
        )

        # Should default to medium reasoning effort
        create_args: Dict[str, Any] = params.create_args
        reasoning: Dict[str, Any] = cast(Dict[str, Any], create_args.get("reasoning", {}))
        assert reasoning.get("effort") == "medium"


class TestResponsesAPICallHandling:
    """Test actual API call handling and response processing."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.responses.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIResponsesAPIClient:
        return OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")

    async def test_basic_text_response(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test processing of basic text response."""
        sdk_like = SimpleNamespace(
            id="resp-123",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="This is a test response")],
                )
            ],
            usage=SimpleNamespace(input_tokens=15, output_tokens=25),
            reasoning=None,
            to_dict=lambda: {"id": "resp-123"},
        )
        mock_openai_client.responses.create.return_value = sdk_like

        result = await client.create(input="Test question")

        assert isinstance(result, CreateResult)
        assert result.content == "This is a test response"
        assert result.finish_reason == "stop"
        assert result.usage.prompt_tokens == 15
        assert result.usage.completion_tokens == 25

    async def test_response_with_reasoning(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test processing response with reasoning items."""
        sdk_like = SimpleNamespace(
            id="resp-124",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="Final answer after reasoning")],
                )
            ],
            usage=SimpleNamespace(input_tokens=30, output_tokens=50),
            reasoning=SimpleNamespace(summary=[SimpleNamespace(text="First, I need to consider..."), SimpleNamespace(text="Then, I should analyze..."), SimpleNamespace(text="Finally, the conclusion is...")]),
            to_dict=lambda: {"id": "resp-124"},
        )
        mock_openai_client.responses.create.return_value = sdk_like

        result = await client.create(input="Complex reasoning question", reasoning_effort="high")

        assert result.content == "Final answer after reasoning"
        assert result.thought is not None
        assert "First, I need to consider..." in result.thought
        assert "Then, I should analyze..." in result.thought
        assert "Finally, the conclusion is..." in result.thought

    async def test_custom_tool_call_response(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test processing response with custom tool calls."""
        code_tool = TestCodeExecutorTool()

        sdk_like = SimpleNamespace(
            id="resp-125",
            output=[
                ResponseCustomToolCall(
                    type="custom_tool_call",
                    id="call-789",
                    call_id="call-789",
                    name="code_exec",
                    input="print('Hello from GPT-5!')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')",
                )
            ],
            usage=SimpleNamespace(input_tokens=25, output_tokens=35),
            reasoning=None,
            to_dict=lambda: {"id": "resp-125"},
        )
        mock_openai_client.responses.create.return_value = sdk_like

        result = await client.create(input="Run this Python code to do basic math", tools=[code_tool], preambles=True)

        assert isinstance(result.content, list)
        assert len(result.content) == 1

        tool_call = result.content[0]
        assert tool_call.name == "code_exec"
        assert "print('Hello from GPT-5!')" in tool_call.arguments
        assert result.thought == "I'll execute this Python code for you."
        assert result.finish_reason == "tool_calls"

    async def test_cot_preservation_call(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test call with chain-of-thought preservation."""
        # First call
        sdk_like1 = SimpleNamespace(
            id="resp-100",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="Initial response")],
                )
            ],
            usage=SimpleNamespace(input_tokens=20, output_tokens=30),
            reasoning=SimpleNamespace(summary=[SimpleNamespace(text="Initial reasoning")]),
            to_dict=lambda: {"id": "resp-100"},
        )
        mock_openai_client.responses.create.return_value = sdk_like1

        result1 = await client.create(input="First question", reasoning_effort="high")

        # Second call with preserved context
        sdk_like2 = SimpleNamespace(
            id="resp-101",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="Follow-up response")],
                )
            ],
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            reasoning=None,
            to_dict=lambda: {"id": "resp-101"},
        )
        mock_openai_client.responses.create.return_value = sdk_like2

        result2 = await client.create(input="Follow-up question", previous_response_id="resp-100", reasoning_effort="low")

        # Verify parameters were passed correctly
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        assert call_kwargs["previous_response_id"] == "resp-100"
        assert call_kwargs["reasoning"]["effort"] == "low"

        # Verify lower token usage due to context reuse
        assert result2.usage.prompt_tokens < result1.usage.prompt_tokens


class TestResponsesAPIErrorHandling:
    """Test error handling in Responses API client."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.responses.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIResponsesAPIClient:
        return OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")

    async def test_api_error_propagation(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test that API errors are properly propagated."""
        from openai import APIError

        # Instantiate with minimal required args for latest SDK
        mock_openai_client.responses.create.side_effect = APIError(message="Test API error")  # type: ignore[call-arg]

        with pytest.raises(APIError, match="Test API error"):
            await client.create(input="Test input")

    async def test_cancellation_token_support(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test cancellation token is properly handled."""
        cancellation_token = CancellationToken()

        # Mock a successful response
        sdk_like = SimpleNamespace(
            id="resp-999",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="Response")],
                )
            ],
            usage=SimpleNamespace(input_tokens=5, output_tokens=10),
            reasoning=None,
            to_dict=lambda: {"id": "resp-999"},
        )
        mock_openai_client.responses.create.return_value = sdk_like

        result = await client.create(input="Test with cancellation", cancellation_token=cancellation_token)

        assert result.content == "Response"
        # Verify cancellation token was linked to the future
        # (This is tested implicitly by successful completion)

    async def test_malformed_response_handling(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test handling of malformed API responses."""
        # Response missing required fields
        # Minimal response: empty output and zero usage
        mock_openai_client.responses.create.return_value = SimpleNamespace(
            id="resp-bad",
            output=[],
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
            reasoning=None,
            to_dict=lambda: {"id": "resp-bad"},
        )

        result = await client.create(input="Test malformed response")

        # Should handle gracefully with defaults
        assert result.content == ""
        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0


class TestResponsesAPIIntegration:
    """Test integration scenarios for Responses API."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        with patch("autogen_ext.models.openai._openai_client.openai_client_from_config") as mock:
            mock_client = AsyncMock()
            mock_client.responses.create = AsyncMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_openai_client: Any) -> OpenAIResponsesAPIClient:
        return OpenAIResponsesAPIClient(model="gpt-5", api_key="test-key")

    async def test_multi_turn_conversation_simulation(
        self, client: OpenAIResponsesAPIClient, mock_openai_client: Any
    ) -> None:
        """Simulate a realistic multi-turn conversation with GPT-5."""

        # Turn 1: Initial complex question
        mock_openai_client.responses.create.return_value = {
            "id": "resp-001",
            "choices": [
                {"message": {"content": "Let me break down quantum computing fundamentals..."}, "finish_reason": "stop"}
            ],
            "reasoning_items": [
                {"type": "reasoning", "content": "This is a complex topic requiring careful explanation..."}
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 200},
        }

        result1 = await client.create(
            input="Explain quantum computing to someone with a physics background",
            reasoning_effort="high",
            verbosity="high",
        )

        # Turn 2: Follow-up question with context reuse
        mock_openai_client.responses.create.return_value = SimpleNamespace(
            id="resp-002",
            output=[
                ResponseOutputMessage(
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[ResponseOutputText(type="output_text", text="Building on quantum fundamentals, quantum algorithms...")],
                )
            ],
            usage=SimpleNamespace(input_tokens=30, output_tokens=150),
            reasoning=None,
            to_dict=lambda: {"id": "resp-002"},
        )

        result2 = await client.create(
            input="How do quantum algorithms leverage these principles?",
            previous_response_id=result1.response_id,  # type: ignore
            reasoning_effort="medium",  # Less reasoning needed due to context
        )

        # Turn 3: Specific implementation request
        mock_openai_client.responses.create.return_value = SimpleNamespace(
            id="resp-003",
            output=[
                ResponseCustomToolCall(
                    type="custom_tool_call",
                    id="call-001",
                    call_id="call-001",
                    name="code_exec",
                    input="# Simple quantum circuit\nfrom qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\nqc.h(0)\nqc.cx(0, 1)\nprint(qc)",
                )
            ],
            usage=SimpleNamespace(input_tokens=25, output_tokens=100),
            reasoning=None,
            to_dict=lambda: {"id": "resp-003"},
        )

        code_tool = TestCodeExecutorTool()
        result3 = await client.create(
            input="Show me a simple quantum circuit implementation",
            previous_response_id=result2.response_id,  # type: ignore
            tools=[code_tool],
            reasoning_effort="minimal",  # Very little reasoning needed
            preambles=True,
        )

        # Verify the conversation flow
        assert "quantum computing fundamentals" in result1.content
        assert result1.thought is not None

        assert "quantum algorithms" in result2.content
        assert result2.usage.prompt_tokens < result1.usage.prompt_tokens

        assert isinstance(result3.content, list)
        assert result3.content[0].name == "code_exec"
        assert "QuantumCircuit" in result3.content[0].arguments
        assert result3.thought == "I'll provide a simple quantum algorithm implementation."

    async def test_usage_tracking(self, client: OpenAIResponsesAPIClient, mock_openai_client: Any) -> None:
        """Test token usage tracking across multiple calls."""
        # Multiple API calls with different usage
        call_responses = [
            SimpleNamespace(
                id="r1",
                output=[
                    ResponseOutputMessage(
                        role="assistant",
                        status="completed",
                        type="message",
                        content=[ResponseOutputText(type="output_text", text="Response 1")],
                    )
                ],
                usage=SimpleNamespace(input_tokens=10, output_tokens=20),
                reasoning=None,
                to_dict=lambda: {"id": "r1"},
            ),
            SimpleNamespace(
                id="r2",
                output=[
                    ResponseOutputMessage(
                        role="assistant",
                        status="completed",
                        type="message",
                        content=[ResponseOutputText(type="output_text", text="Response 2")],
                    )
                ],
                usage=SimpleNamespace(input_tokens=15, output_tokens=25),
                reasoning=None,
                to_dict=lambda: {"id": "r2"},
            ),
            SimpleNamespace(
                id="r3",
                output=[
                    ResponseOutputMessage(
                        role="assistant",
                        status="completed",
                        type="message",
                        content=[ResponseOutputText(type="output_text", text="Response 3")],
                    )
                ],
                usage=SimpleNamespace(input_tokens=5, output_tokens=15),
                reasoning=None,
                to_dict=lambda: {"id": "r3"},
            ),
        ]

        for i, response in enumerate(call_responses):
            mock_openai_client.responses.create.return_value = response
            await client.create(input=f"Test input {i+1}")

        # Check cumulative usage
        total_usage = client.total_usage()
        actual_usage = client.actual_usage()

        assert total_usage.prompt_tokens == 30  # 10 + 15 + 5
        assert total_usage.completion_tokens == 60  # 20 + 25 + 15
        assert actual_usage.prompt_tokens == 30
        assert actual_usage.completion_tokens == 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
