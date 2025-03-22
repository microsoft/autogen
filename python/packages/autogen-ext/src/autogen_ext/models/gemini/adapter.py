"""
Type definitions and conversion functions between AutoGen and google.genai types.
This adapter layer provides helper functions to convert AutoGen message content
(e.g., text and image) into google.genai types.Part objects.
"""

import base64
from typing import Dict, List, Optional, Sequence, Union, Any

from autogen_core import FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from google.genai import types  # type: ignore
from typing_extensions import AsyncGenerator, Union, Unpack


def _image_to_part(image: Image) -> types.Part:
    """Convert an AutoGen Image to a Gemini Part."""
    # NOTE: to_base64() returns PNG format by default
    image_bytes = base64.b64decode(image.to_base64())
    return types.Part.from_bytes(data=image_bytes, mime_type="image/png")


def _text_to_part(text: str) -> types.Part:
    """Convert text to a Gemini Part."""
    return types.Part.from_text(text=text)


def _function_call_to_part(func_call: FunctionCall) -> types.Part:
    """Convert a FunctionCall to a Gemini Part."""
    return types.Part.from_function_call(name=func_call.name, args=func_call.arguments)


def _content_to_parts(content: Union[str, List[Union[str, Image, FunctionCall]]]) -> List[types.Part]:
    """Convert mixed content to a list of Gemini Parts.

    Args:
        content: Can be either a string or a list containing strings, Images, or FunctionCalls

    Returns:
        List of Gemini Part objects

    Raises:
        ValueError: If content contains unsupported types
    """
    if isinstance(content, str):
        return [_text_to_part(content)]

    if not isinstance(content, list):
        raise ValueError(f"Unsupported content type: {type(content)}")

    parts: List[types.Part] = []
    for item in content:
        if isinstance(item, str):
            parts.append(_text_to_part(item))
        elif isinstance(item, Image):
            parts.append(_image_to_part(item))
        elif isinstance(item, FunctionCall):
            parts.append(_function_call_to_part(item))
        else:
            raise ValueError(f"Unsupported content type: {type(item)}")

    return parts


def _system_message_to_content(message: SystemMessage) -> types.Content:
    """Convert a SystemMessage to a Gemini Content object."""
    return types.Content(role="user", parts=_content_to_parts(message.content))


def _user_message_to_content(message: UserMessage) -> types.Content:
    """Convert a UserMessage to a Gemini Content object."""
    if isinstance(message.content, str):
        return types.Content(role="user", parts=[_text_to_part(message.content)])
    else:
        parts: List[types.Part] = []
        for item in message.content:
            if isinstance(item, str):
                parts.append(_text_to_part(item))
            elif isinstance(item, Image):
                parts.append(_image_to_part(item))
            else:
                raise ValueError(f"Unknown content type: {type(item)}")
        return types.Content(role="user", parts=parts)


def _assistant_message_to_content(message: AssistantMessage) -> types.Content:
    """Convert an AssistantMessage to a Gemini Content object."""
    if isinstance(message.content, str):
        return types.Content(role="model", parts=[_text_to_part(message.content)])
    elif isinstance(message.content, list):
        parts = []
        for item in message.content:
            if isinstance(item, FunctionCall):
                parts.append(_function_call_to_part(item))
            else:
                raise ValueError(f"Unsupported content type in AssistantMessage: {type(item)}")
        return types.Content(role="model", parts=parts)
    else:
        raise ValueError(f"Unsupported content type in AssistantMessage: {type(message.content)}")


def _tool_message_to_content(message: FunctionExecutionResultMessage) -> types.Content:
    """Convert a FunctionExecutionResultMessage to a Gemini Content object."""
    parts = []
    for result in message.content:
        parts.append(
            types.Part.from_function_response(
                name=result.call_id,
                response={
                    "result": result.content if not result.is_error else None,
                    "error": result.content if result.is_error else None,
                },
            )
        )
    return types.Content(role="tool", parts=parts)


def to_gemini_content(message: LLMMessage) -> types.Content:
    """Convert an AutoGen LLMMessage to a Gemini Content object."""
    if isinstance(message, SystemMessage):
        return _system_message_to_content(message)
    elif isinstance(message, UserMessage):
        return _user_message_to_content(message)
    elif isinstance(message, AssistantMessage):
        return _assistant_message_to_content(message)
    elif isinstance(message, FunctionExecutionResultMessage):
        return _tool_message_to_content(message)
    else:
        raise ValueError(f"Unsupported message type: {message.type}")


def prepare_genai_contents(messages: Sequence[LLMMessage]) -> List[types.Content]:
    """Convert a sequence of LLMMessages to a list of Gemini API Content objects."""
    contents: List[types.Content] = []
    for message in messages:
        contents.append(to_gemini_content(message))
    return contents


def convert_tool(tool: Union[Tool, ToolSchema]) -> types.Tool:
    """
    Convert an AutoGen tool to a Gemini tool.

    Args:
        tool: Either a Tool instance or ToolSchema dictionary to convert

    Returns:
        types.Tool: Gemini tool representation with function declarations

    Raises:
        ValueError: If the tool schema is missing required fields
    """
    # Get a copy of the tool schema to avoid modifying the original
    if isinstance(tool, Tool):
        tool_schema = tool.schema.copy()
    else:
        tool_schema = tool.copy()

    # Validate required fields
    if not isinstance(tool_schema.get("name"), str):
        raise ValueError("Tool schema must contain a 'name' string field")

    # Clean up tool parameters by removing "title" if present
    parameters = tool_schema.get("parameters", {})
    if isinstance(parameters, dict):
        if "properties" in parameters:
            for prop in parameters["properties"].values():
                if isinstance(prop, dict):
                    if "title" in prop:
                        del prop["title"]

    # Convert parameters to Gemini schema
    schema = None
    if parameters:
        schema = types.Schema.from_dict(parameters)

    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=tool_schema["name"],
                description=tool_schema.get("description", ""),
                parameters=schema,
            )
        ]
    )


def convert_tools(tools: Sequence[Union[Tool, ToolSchema]]) -> List[types.Tool]:
    """Convert AutoGen tools to Gemini function declarations."""
    converted: List[types.Tool] = []
    for tool in tools:
        converted.append(convert_tool(tool))
    return converted


def _convert_single_safety_setting(category: str, settings: Dict[str, str]) -> types.SafetySetting:
    """Convert a single safety setting to types.SafetySetting.

    Args:
        category: The safety category
        settings: Dictionary containing the threshold setting

    Returns:
        types.SafetySetting

    Raises:
        ValueError: If settings is empty or missing threshold
    """
    if not settings:
        raise ValueError(f"Settings for category '{category}' cannot be empty")

    threshold = settings.get("threshold")
    if threshold is None:
        raise ValueError(f"Missing 'threshold' in settings for category '{category}'")

    return types.SafetySetting(category=category, threshold=threshold)


def convert_safety_settings(safety_settings: Optional[Dict[str, Dict[str, str]]]) -> List[types.SafetySetting]:
    """Convert a dictionary of safety settings to a list of types.SafetySetting.

    Args:
        safety_settings: Dictionary mapping safety categories to their settings.
            Expected format: {category: {"threshold": value}}

    Returns:
        List of types.SafetySetting objects

    Raises:
        ValueError: If safety_settings is empty or contains invalid settings
    """
    if not safety_settings:
        raise ValueError("Safety settings cannot be empty")

    converted_settings = []
    for category, settings in safety_settings.items():
        try:
            setting = _convert_single_safety_setting(category, settings)
            converted_settings.append(setting)
        except ValueError as e:
            raise ValueError("Invalid safety settings") from e

    return converted_settings


def to_generate_content_config(
    **kwargs: Unpack[types.GenerateContentConfigDict],
) -> types.GenerateContentConfigDict:
    """Convert a dictionary to a GenerateContentConfigDict."""
    return types.GenerateContentConfigDict(**kwargs)


def to_generate_images_config(**kwargs: Unpack[types.GenerateImagesConfigDict]) -> types.GenerateImagesConfigDict:
    """Convert a dictionary to a GenerateImagesConfigDict."""
    return types.GenerateImagesConfigDict(**kwargs)


def prepare_config(
    config: Optional[Union[types.GenerateContentConfig, Dict[str, Any]]] = None,
    create_args: Dict[str, Any] = {},
    extra_create_args: Dict[str, Any] = {},
    tools: Optional[List[types.Tool]] = None,
    response_format: Optional[Dict[str, Any]] = None,
) -> Union[types.GenerateContentConfig, types.GenerateImagesConfig]:
    """
    Prepare and merge a configuration object for content generation.
    """
    if config is None:
        prepared_config = types.GenerateContentConfig()
    elif isinstance(config, dict):
        prepared_config = types.GenerateContentConfig(**config)
    else:
        prepared_config = config

    if tools is not None:
        prepared_config.tools = tools

    # Merge all configuration arguments
    merged_args = {**create_args, **dict(extra_create_args)}
    for key, value in merged_args.items():
        try:
            setattr(prepared_config, key, value)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not set config attribute {key}: {e}")

    # Store response format in generation config metadata
    if response_format is not None:
        try:
            prepared_config.__dict__["response_format"] = response_format
        except Exception as e:
            logger.debug(f"Could not set response_format: {e}")

    return prepared_config
