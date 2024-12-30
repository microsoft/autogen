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

@pytest.mark.asyncio
async def test_sk_chat_completion_with_tools():
    # Set up Azure OpenAI client with token auth
    deployment_name = "gpt-4o-mini"
    endpoint = "https://<your-endpoint>.openai.azure.com/"
    api_version = "2024-07-18"
    
    # Create SK client
    sk_client = AzureChatCompletion(
        deployment_name=deployment_name,
        endpoint=endpoint,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )
    
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
    assert isinstance(result.content, str)
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens >= 0
    assert result.usage.completion_tokens >= 0
    assert not result.cached
