from typing import List

import pytest
from agnext.components import Image
from agnext.components.models import (
    AssistantMessage,
    AzureOpenAIChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    OpenAIChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import FunctionTool


@pytest.mark.asyncio
async def test_openai_chat_completion_client() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    assert client


@pytest.mark.asyncio
async def test_azure_openai_chat_completion_client() -> None:
    client = AzureOpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="api_key",
        api_version="2020-08-04",
        azure_endpoint="https://dummy.com",
        model_capabilities={"vision": True, "function_calling": True, "json_output": True},
    )
    assert client


@pytest.mark.asyncio
async def test_openai_chat_completion_client_count_tokens() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key="api_key")
    messages : List[LLMMessage] = [
        SystemMessage(content="Hello"),
        UserMessage(content="Hello", source="user"),
        AssistantMessage(content="Hello", source="assistant"),
        UserMessage(
            content=[
                "str1",
                Image.from_base64(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
                ),
            ],
            source="user",
        ),
        FunctionExecutionResultMessage(content=[FunctionExecutionResult(content="Hello", call_id="1")]),
    ]

    def tool1(test: str, test2: str) -> str:
        return test + test2

    def tool2(test1: int, test2: List[int]) -> str:
        return str(test1) + str(test2)

    tools = [FunctionTool(tool1, description="example tool 1"), FunctionTool(tool2, description="example tool 2")]
    num_tokens = client.count_tokens(messages, tools=tools)
    assert num_tokens

    remaining_tokens = client.remaining_tokens(messages, tools=tools)
    assert remaining_tokens
