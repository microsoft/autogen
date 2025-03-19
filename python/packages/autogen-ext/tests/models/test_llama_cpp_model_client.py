import contextlib
import sys
from typing import TYPE_CHECKING, Any, ContextManager, Generator, List, Sequence, Union

import pytest
import torch

# from autogen_agentchat.agents import AssistantAgent
# from autogen_agentchat.messages import TextMessage
# from autogen_core import CancellationToken
from autogen_core.models import RequestUsage, SystemMessage, UserMessage
from llama_cpp import ChatCompletionRequestResponseFormat
from pydantic import BaseModel

# from autogen_core.tools import FunctionTool
try:
    from llama_cpp import ChatCompletionMessageToolCalls

    if TYPE_CHECKING:
        from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient
except ImportError:
    # If llama_cpp is not installed, we can't run the tests.
    pytest.skip("Skipping LlamaCppChatCompletionClient tests: llama-cpp-python not installed", allow_module_level=True)


class AgentResponse(BaseModel):
    """A response from the agent."""

    thoughts: str
    content: str


# Fake Llama class to simulate responses
class FakeLlama:
    def __init__(
        self,
        model_path: str,
        **_: Any,
    ) -> None:
        self.model_path = model_path
        self.n_ctx = lambda: 1024
        self._structured_response = AgentResponse(thoughts="Test thoughts", content="Test content")

    # Added tokenize method for testing purposes.
    def tokenize(self, b: bytes) -> list[int]:
        return list(b)

    def create_chat_completion(
        self,
        messages: Any,
        tools: List[ChatCompletionMessageToolCalls] | None,
        stream: bool = False,
        response_format: ChatCompletionRequestResponseFormat | None = None,
    ) -> dict[str, Any]:
        # Return fake non-streaming response.

        if response_format is not None:
            assert self._structured_response is not None
            # If response_format is provided, return a different format.
            return {
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                "choices": [{"message": {"content": self._structured_response.model_dump_json()}}],
            }

        return {
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            "choices": [{"message": {"content": "Fake response"}}],
        }

    def __call__(self, prompt: str, stream: bool = True) -> Generator[dict[str, Any], None, None]:
        # Yield fake streaming tokens.
        yield {"choices": [{"text": "Hello "}]}
        yield {"choices": [{"text": "World"}]}


@pytest.fixture
@contextlib.contextmanager
def get_completion_client(
    monkeypatch: pytest.MonkeyPatch,
) -> "Generator[type[LlamaCppChatCompletionClient], None, None]":
    with monkeypatch.context() as m:
        m.setattr("llama_cpp.Llama", FakeLlama)
        from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient

        yield LlamaCppChatCompletionClient
    sys.modules.pop("autogen_ext.models.llama_cpp._llama_cpp_completion_client", None)
    sys.modules.pop("llama_cpp", None)


@pytest.mark.asyncio
async def test_llama_cpp_create(get_completion_client: "ContextManager[type[LlamaCppChatCompletionClient]]") -> None:
    with get_completion_client as Client:
        client = Client(model_path="dummy")
        messages: Sequence[Union[SystemMessage, UserMessage]] = [
            SystemMessage(content="Test system"),
            UserMessage(content="Test user", source="user"),
        ]
        result = await client.create(messages=messages)
        assert result.content == "Fake response"
        usage: RequestUsage = result.usage
        assert usage.prompt_tokens == 1
        assert usage.completion_tokens == 2
        assert result.finish_reason in ("stop", "unknown")


@pytest.mark.asyncio
async def test_llama_cpp_create_structured_output(
    get_completion_client: "ContextManager[type[LlamaCppChatCompletionClient]]",
) -> None:
    with get_completion_client as Client:
        client = Client(model_path="dummy")
        messages: Sequence[Union[SystemMessage, UserMessage]] = [
            SystemMessage(content="Test system"),
            UserMessage(content="Test user", source="user"),
        ]
        result = await client.create(messages=messages, json_output=AgentResponse)
        assert isinstance(result.content, str)
        assert AgentResponse.model_validate_json(result.content).thoughts == "Test thoughts"
        assert AgentResponse.model_validate_json(result.content).content == "Test content"


# Commmented out due to raising not implemented error will leave in case streaming is supported in the future.
# @pytest.mark.asyncio
# async def test_llama_cpp_create_stream(
#     get_completion_client: "ContextManager[type[LlamaCppChatCompletionClient]]",
# ) -> None:
#     with get_completion_client as Client:
#         client = Client(filename="dummy")
#         messages: Sequence[Union[SystemMessage, UserMessage]] = [
#             SystemMessage(content="Test system"),
#             UserMessage(content="Test user", source="user"),
#         ]
#         collected = ""
#         async for token in client.create_stream(messages=messages):
#             collected += token
#         assert collected == "Hello World"


@pytest.mark.asyncio
async def test_create_invalid_message(
    get_completion_client: "ContextManager[type[LlamaCppChatCompletionClient]]",
) -> None:
    with get_completion_client as Client:
        client = Client(model_path="dummy")
        # Pass an unsupported message type (integer) to trigger ValueError.
        with pytest.raises(ValueError, match="Unsupported message type"):
            await client.create(messages=[123])  # type: ignore


@pytest.mark.asyncio
async def test_count_and_remaining_tokens(
    get_completion_client: "ContextManager[type[LlamaCppChatCompletionClient]]", monkeypatch: pytest.MonkeyPatch
) -> None:
    with get_completion_client as Client:
        client = Client(model_path="dummy")
        msg = SystemMessage(content="Test")
        # count_tokens should count the bytes
        token_count = client.count_tokens([msg])
        # Since "Test" encoded is 4 bytes, expect 4 tokens.
        assert token_count >= 4
        remaining = client.remaining_tokens([msg])
        # remaining should be (1024 - token_count); ensure non-negative.
        assert remaining == max(1024 - token_count, 0)


@pytest.mark.asyncio
async def test_llama_cpp_integration_non_streaming() -> None:
    if not ((hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or torch.cuda.is_available()):
        pytest.skip("Skipping LlamaCpp integration tests: GPU not available not set")

    from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient

    client = LlamaCppChatCompletionClient(
        repo_id="unsloth/phi-4-GGUF",
        filename="phi-4-Q2_K_L.gguf",
        n_gpu_layers=-1,
        seed=1337,
        n_ctx=5000,
        verbose=False,
    )
    messages: Sequence[Union[SystemMessage, UserMessage]] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Hello, how are you?", source="user"),
    ]
    result = await client.create(messages=messages)
    assert isinstance(result.content, str) and len(result.content.strip()) > 0


@pytest.mark.asyncio
async def test_llama_cpp_integration_non_streaming_structured_output() -> None:
    if not ((hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or torch.cuda.is_available()):
        pytest.skip("Skipping LlamaCpp integration tests: GPU not available not set")

    from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient

    client = LlamaCppChatCompletionClient(
        repo_id="unsloth/phi-4-GGUF",
        filename="phi-4-Q2_K_L.gguf",
        n_gpu_layers=-1,
        seed=1337,
        n_ctx=5000,
        verbose=False,
    )
    messages: Sequence[Union[SystemMessage, UserMessage]] = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Hello, how are you?", source="user"),
    ]
    result = await client.create(messages=messages, json_output=AgentResponse)
    assert isinstance(result.content, str) and len(result.content.strip()) > 0
    assert AgentResponse.model_validate_json(result.content)


# Commmented out due to raising not implemented error will leave in case streaming is supported in the future.
# @pytest.mark.asyncio
# async def test_llama_cpp_integration_streaming() -> None:
#     if not ((hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or torch.cuda.is_available()):
#         pytest.skip("Skipping LlamaCpp integration tests: GPU not available not set")

#     from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient
#     client = LlamaCppChatCompletionClient(
#         repo_id="unsloth/phi-4-GGUF", filename="phi-4-Q2_K_L.gguf", n_gpu_layers=-1, seed=1337, n_ctx=5000
#     )
#     messages: Sequence[Union[SystemMessage, UserMessage]] = [
#         SystemMessage(content="You are a helpful assistant."),
#         UserMessage(content="Please stream your response.", source="user"),
#     ]
#     collected = ""
#     async for token in client.create_stream(messages=messages):
#         collected += token
#     assert isinstance(collected, str) and len(collected.strip()) > 0

# Commented out tool use as this functionality is not yet implemented for Phi-4.
# Define tools (functions) for the AssistantAgent
# def add(num1: int, num2: int) -> int:
#     """Add two numbers together"""
#     return num1 + num2


# @pytest.mark.asyncio
# async def test_llama_cpp_integration_tool_use() -> None:
#     if not ((hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or torch.cuda.is_available()):
#         pytest.skip("Skipping LlamaCpp integration tests: GPU not available not set")

#     from autogen_ext.models.llama_cpp._llama_cpp_completion_client import LlamaCppChatCompletionClient

#     model_client = LlamaCppChatCompletionClient(
#         repo_id="unsloth/phi-4-GGUF", filename="phi-4-Q2_K_L.gguf", n_gpu_layers=-1, seed=1337, n_ctx=5000
#     )

#     # Initialize the AssistantAgent
#     assistant = AssistantAgent(
#         name="assistant",
#         system_message=("You can add two numbers together using the `add` function. "),
#         model_client=model_client,
#         tools=[
#             FunctionTool(
#                 add,
#                 description="Add two numbers together. The first argument is num1 and second is num2. The return value is num1 + num2",
#             )
#         ],
#         reflect_on_tool_use=True,  # Reflect on tool results
#     )

#     # Test the tool
#     response = await assistant.on_messages(
#         [
#             TextMessage(content="add 3 and 4", source="user"),
#         ],
#         CancellationToken(),
#     )

#     assert "7" in response.chat_message.content
