import json
from typing import Any, Dict, List, Optional

import pytest
from autogen_core import FunctionCall
from autogen_core.models import RequestUsage
from autogen_ext.models.gemini.utils import (
    extract_tool_calls,
    get_response_text,
    get_response_usage,
    handle_structured_output,
    map_finish_reason,
    prepare_config,
)
from google.genai import types  # type: ignore
from pydantic import BaseModel


class TestModel(BaseModel):
    name: str
    value: int

@pytest.mark.parametrize("finish_reason,expected", [
    ("STOP", "stop"),
    ("MAX_TOKENS", "length"),
    ("SAFETY", "content_filter"),
    ("RECITATION", "content_filter"),
    ("FUNCTION_CALLS", "function_calls"),
    ("OTHER", "unknown"),
    (None, "unknown"),
    ("INVALID", "unknown"),
])
def test_map_finish_reason(finish_reason: Optional[str], expected: str):
    assert map_finish_reason(finish_reason) == expected

def test_prepare_config():
    # Test with empty config
    config = prepare_config()
    assert isinstance(config, types.GenerateContentConfig)

    # Test with dict config
    config = prepare_config({"temperature": 0.5})
    assert config.temperature == 0.5

    # Test with tools
    tools = [types.Tool(function_declarations=[types.FunctionDeclaration(name="test")])]
    config = prepare_config(tools=tools)
    assert len(config.tools[0].function_declarations) == 1

    # Test with response format
    response_format = {"type": "json_object"}
    config = prepare_config(response_format=response_format)
    assert config.__dict__.get("response_format") == response_format

@pytest.mark.parametrize("text,response_format,expected", [
    ("plain text", None, "plain text"),
    ('{"key": "value"}', {"type": "json_object"}, {"key": "value"}),
    ('{"name": "test", "value": 1}', {"type": "pydantic", "schema": TestModel}, TestModel(name="test", value=1)),
    ("invalid json", {"type": "json_object"}, "invalid json"),
])
def test_handle_structured_output(text: str, response_format: Optional[Dict[str, Any]], expected: Any):
    result = handle_structured_output(text, response_format)
    if isinstance(expected, BaseModel):
        assert isinstance(result, type(expected))
        assert result.dict() == expected.dict()
    else:
        assert result == expected

def test_extract_tool_calls():
    # Create mock response with function calls
    function_call = types.FunctionCall(name="test", args={"param": "value"})
    part = types.Part(function_call=function_call)
    content = types.Content(parts=[part])
    candidate = types.Candidate(content=content)
    response = types.GenerateContentResponse(candidates=[candidate])

    tool_calls = extract_tool_calls(response)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "test"
    assert json.loads(tool_calls[0].arguments) == {"param": "value"}

def test_get_response_text():
    # Create mock response with text parts
    part1 = types.Part(text="Hello")
    part2 = types.Part(text=" World")
    content = types.Content(parts=[part1, part2])
    candidate = types.Candidate(content=content)
    response = types.GenerateContentResponse(candidates=[candidate])

    assert get_response_text(response) == "Hello World"

def test_get_response_usage():
    # Create mock response with usage data
    try:
        usage_metadata = types.UsageMetadata(
            prompt_token_count=10,
            candidates_token_count=20
        )
    except AttributeError:
        class UsageMetadata:
            def __init__(self, prompt_token_count, candidates_token_count):
                self.prompt_token_count = prompt_token_count
                self.candidates_token_count = candidates_token_count
        usage_metadata = UsageMetadata(
            prompt_token_count=10,
            candidates_token_count=20
        )
    response = types.GenerateContentResponse(usage_metadata=usage_metadata)

    usage = get_response_usage(response)
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
