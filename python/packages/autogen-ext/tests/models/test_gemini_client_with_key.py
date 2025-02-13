import json
import os
from typing import Optional

import pytest
from autogen_core import Image
from autogen_core.models import CreateResult, UserMessage
from autogen_core.tools import FunctionTool
from pydantic import BaseModel, Field

from autogen_ext.models.gemini import GeminiChatCompletionClient

try:
    api_key: Optional[str] = os.environ["GEMINI_API_KEY"]
    has_gemini_key = True
except KeyError:
    api_key = None
    has_gemini_key = False

# Test models from Gemini 2.0 and 1.5 families
TEST_MODELS: list[str] = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    # "gemini-2.0-pro",
]

class MathResult(BaseModel):
    formula: str = Field(..., description="Formula to solve")
    result: float = Field(..., description="Result of the operation")

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_basic_math(model: str):
    gemini_client = GeminiChatCompletionClient(model=model, api_key=api_key)
    messages = [UserMessage(content="What is 2 + 2?", source="user")]

    result = await gemini_client.create(messages)

    assert isinstance(result, CreateResult)
    assert isinstance(result.content, str)
    assert "4" in result.content

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_json_math(model: str):
    gemini_client = GeminiChatCompletionClient(model=model, api_key=api_key)
    messages = [
        UserMessage(
            content="Solve 3 * 5 and return the result as JSON with formula and result fields.",
            source="user",
        )
    ]

    result = await gemini_client.create(
        messages,
        json_output=True,
        extra_create_args={"response_format": {"schema_": MathResult}}
    )

    assert isinstance(result, CreateResult)
    assert isinstance(result.content, str)

    # Parse and validate JSON
    content = result.content.strip().lstrip("```json").rstrip("```").strip()
    parsed_content = json.loads(content)
    assert isinstance(parsed_content, dict)

    # Validate using MathResult model
    math_result = MathResult.model_validate(parsed_content)
    assert math_result.formula != ""
    assert math_result.result == 15.0

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_streaming(model: str):
    gemini_client = GeminiChatCompletionClient(model=model, api_key=api_key)
    messages = [UserMessage(content="Count from 1 to 3", source="user")]

    response = ""
    async for chunk in gemini_client.create_stream(messages):
        if isinstance(chunk, str):
            response += chunk
        elif isinstance(chunk, CreateResult):
            response += chunk.content

    assert isinstance(response, str)
    assert all(str(i) in response for i in range(1, 4))

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_function_calling(model: str):
    gemini_client = GeminiChatCompletionClient(model=model, api_key=api_key)

    async def add_numbers(a: float, b: float) -> float:
        return a + b

    function_tool = FunctionTool(
        add_numbers,
        description="Adds two numbers together"
    )

    messages = [UserMessage(content="Add 2.5 and 3.7", source="user")]
    result = await gemini_client.create(messages, tools=[function_tool])

    assert isinstance(result, CreateResult)
    if result.finish_reason == "function_calls":
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert result.content[0].name == "add_numbers"
        assert "a" in result.content[0].arguments
        assert "b" in result.content[0].arguments
    else:
        assert isinstance(result.content, str)
        assert "6.2" in result.content

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_safety_settings(model: str):
    gemini_client = GeminiChatCompletionClient(
        model=model,
        api_key=api_key,
        # Correct safety settings format - categories should map to thresholds directly
        safety_settings={
            "HARM_CATEGORY_HARASSMENT": "BLOCK_LOW_AND_ABOVE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
        }
        # Previous incorrect format: safety_settings={"HARM_CATEGORY_DANGEROUS_CONTENT": {"threshold": "BLOCK_ONLY_HIGH",}}
    )

    messages = [UserMessage(content="What is 2 + 2?", source="user")]
    result = await gemini_client.create(messages)

    assert isinstance(result, CreateResult)
    assert isinstance(result.content, str)
    assert "4" in result.content

@pytest.mark.skipif(not has_gemini_key, reason="requires GEMINI_API_KEY environment variable")
@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
async def test_gemini_token_counting(model: str):
    gemini_client = GeminiChatCompletionClient(model=model, api_key=api_key)
    messages = [UserMessage(content="What is 2 + 2?", source="user")]

    result = await gemini_client.create(messages)

    assert isinstance(result, CreateResult)
    assert isinstance(result.usage.prompt_tokens, int)
    assert result.usage.completion_tokens is not None
