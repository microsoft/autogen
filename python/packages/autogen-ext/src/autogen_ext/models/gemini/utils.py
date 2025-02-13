"""Utility functions for Gemini API integration."""

import json
from typing import Any, Dict, List, Literal, Optional, Union

from autogen_core import FunctionCall
from autogen_core.models import ModelFamily, ModelInfo, RequestUsage
from google.genai import types  # type: ignore


def map_finish_reason(
    finish_reason: Optional[str],
) -> Literal["stop", "length", "function_calls", "content_filter", "unknown"]:
    """Map Gemini API finish reasons to standardized finish reasons."""
    if not finish_reason:
        return "unknown"

    finish_reason = finish_reason.upper()
    finish_reason_map: Dict[str, Literal["stop", "length", "function_calls", "content_filter", "unknown"]] = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "content_filter",
        "RECITATION": "content_filter",
        "BLOCKLIST": "content_filter",
        "PROHIBITED_CONTENT": "content_filter",
        "SPII": "content_filter",
        "FUNCTION_CALLS": "function_calls",
        "MALFORMED_FUNCTION_CALL": "unknown",
        "OTHER": "unknown",
        "FINISH_REASON_UNSPECIFIED": "unknown",
    }
    return finish_reason_map.get(finish_reason, "unknown")


def handle_structured_output(text: str, response_format: Optional[Dict[str, Any]] = None) -> Any:
    """
    Handle structured output based on the response format.
    """
    if not response_format or response_format.get("type") == "text":
        return text

    output_type = response_format.get("type", "text")
    schema = response_format.get("schema")

    try:
        # First try to parse as JSON regardless of output type
        result = json.loads(text.strip())

        if output_type == "json_object":
            return result
        elif output_type == "pydantic" and schema and hasattr(schema, "model_validate"):
            try:
                return schema.model_validate(result)
            except Exception:
                # Return raw dict if Pydantic validation fails
                return result

        return result
    except json.JSONDecodeError:
        return text


def extract_tool_calls(response: types.GenerateContentResponse) -> List[FunctionCall]:
    """Extract tool calls from a Gemini response."""
    tool_calls: List[FunctionCall] = []

    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_calls.append(
                    FunctionCall(
                        id=str(len(tool_calls)),
                        name=part.function_call.name,
                        arguments=json.dumps(part.function_call.args),
                    )
                )

    return tool_calls


def get_response_text(response: types.GenerateContentResponse) -> str:
    """Extract text content from a Gemini response."""
    text = ""
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text"):
                text += part.text
    return text


def get_response_usage(response: types.GenerateContentResponse) -> RequestUsage:
    """Extract token usage from a Gemini response."""
    return RequestUsage(
        prompt_tokens=response.usage_metadata.prompt_token_count,
        completion_tokens=response.usage_metadata.candidates_token_count,
    )


def can_generate_images(model_info: ModelInfo) -> bool:
    """Check if the model can generate images."""
    image_generation_families = [ModelFamily.IMAGEN_3_0]
    if model_info.get("family") in image_generation_families:
        return True
    return False
