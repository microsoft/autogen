import os
import pytest
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.kernel import Kernel
from semantic_kernel.memory.null_memory import NullMemory
from autogen_core.models import SystemMessage, UserMessage
from autogen_core.tools import BaseTool
from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
from pydantic import BaseModel
from autogen_core import CancellationToken

class CalculatorArgs(BaseModel):
    a: float
    b: float

class CalculatorResult(BaseModel):
    result: float

class CalculatorTool(BaseTool[CalculatorArgs, CalculatorResult]):
    def __init__(self):
        super().__init__(
            args_type=CalculatorArgs,
            return_type=CalculatorResult,
            name="calculator",
            description="Add two numbers together"
        )

    async def run(self, args: CalculatorArgs, cancellation_token: CancellationToken) -> CalculatorResult:
        return CalculatorResult(result=args.a + args.b)

@pytest.fixture
def sk_client():
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    return AzureChatCompletion(
        deployment_name=deployment_name,
        endpoint=endpoint,
        api_key=api_key,
    )

@pytest.mark.asyncio
async def test_sk_chat_completion_with_tools(sk_client):
    # Create adapter
    adapter = SKChatCompletionAdapter(sk_client)
    
    # Create kernel
    kernel = Kernel(memory=NullMemory())
    
    # Create calculator tool instance
    tool = CalculatorTool()
    
    # Test messages
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 2 + 2?", source="user"),
    ]
    
    # Call create with tool
    result = await adapter.create(
        messages=messages,
        tools=[tool],
        extra_create_args={"kernel": kernel}
    )
    
    # Verify response
    assert isinstance(result.content, list)
    assert result.finish_reason == "function_calls"
    assert result.usage.prompt_tokens >= 0
    assert result.usage.completion_tokens >= 0
    assert not result.cached

@pytest.mark.asyncio
async def test_sk_chat_completion_without_tools(sk_client):
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())
    
    # Test messages
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Say hello!", source="user"),
    ]
    
    # Call create without tools
    result = await adapter.create(
        messages=messages,
        extra_create_args={"kernel": kernel}
    )
    
    # Verify response
    assert isinstance(result.content, str)
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens >= 0
    assert result.usage.completion_tokens >= 0
    assert not result.cached

@pytest.mark.asyncio
async def test_sk_chat_completion_stream_with_tools(sk_client):
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())
    
    # Create calculator tool
    tool = CalculatorTool()
    
    # Test messages
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="What is 2 + 2?", source="user"),
    ]
    
    # Call create_stream with tool
    response_chunks = []
    async for chunk in adapter.create_stream(
        messages=messages,
        tools=[tool],
        extra_create_args={"kernel": kernel}
    ):
        response_chunks.append(chunk)
    
    # Verify response
    assert len(response_chunks) > 0
    final_chunk = response_chunks[-1]
    assert isinstance(final_chunk.content, list)  # Function calls
    assert final_chunk.finish_reason == "function_calls"
    assert final_chunk.usage.prompt_tokens >= 0
    assert final_chunk.usage.completion_tokens >= 0
    assert not final_chunk.cached

@pytest.mark.asyncio
async def test_sk_chat_completion_stream_without_tools(sk_client):
    # Create adapter and kernel
    adapter = SKChatCompletionAdapter(sk_client)
    kernel = Kernel(memory=NullMemory())
    
    # Test messages
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="Say hello!", source="user"),
    ]
    
    # Call create_stream without tools
    response_chunks = []
    async for chunk in adapter.create_stream(
        messages=messages,
        extra_create_args={"kernel": kernel}
    ):
        response_chunks.append(chunk)
    
    # Verify response
    assert len(response_chunks) > 0
    # All chunks except last should be strings
    for chunk in response_chunks[:-1]:
        assert isinstance(chunk, str)
    
    # Final chunk should be CreateResult
    final_chunk = response_chunks[-1]
    assert isinstance(final_chunk.content, str)
    assert final_chunk.finish_reason == "stop"
    assert final_chunk.usage.prompt_tokens >= 0
    assert final_chunk.usage.completion_tokens >= 0
    assert not final_chunk.cached
