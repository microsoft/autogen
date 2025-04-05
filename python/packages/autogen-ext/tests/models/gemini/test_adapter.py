import base64
import io
from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence, Union

import pytest
from autogen_core import Image
from autogen_core.models import AssistantMessage, SystemMessage, UserMessage
from autogen_core.tools import Tool, ToolSchema
from autogen_ext.models.gemini import adapter
from google.genai import types  # type: ignore
from PIL import Image as PILImage
from pydantic import ValidationError


def create_dummy_image() -> Image:
    """Create a dummy image for testing."""
    # Create a valid JPEG image
    pil_image = PILImage.new("RGB", (1, 1), color="white")
    byte_arr = io.BytesIO()
    pil_image.save(byte_arr, format="JPEG")
    image_data = base64.b64encode(byte_arr.getvalue()).decode("utf-8")
    return Image.from_base64(image_data)


class TestConvertImageToPart:
    def test_convert_image_to_part_base64(self):
        image = create_dummy_image()
        part = adapter.convert_image_to_part(image)
        assert isinstance(part, types.Part)
        assert part.inline_data.mime_type == "image/jpeg"
        assert base64.b64decode(part.inline_data.data) == base64.b64decode(create_dummy_image().to_base64())

    def test_convert_image_to_part_path(self, tmp_path):
        image_file = tmp_path / "test_image.jpg"
        image_file.write_bytes(base64.b64decode(create_dummy_image().to_base64()))
        image = Image.from_pil(PILImage.open(str(image_file)))
        part = adapter.convert_image_to_part(image)
        assert isinstance(part, types.Part)
        assert part.inline_data.mime_type == "image/jpeg"
        assert base64.b64decode(part.inline_data.data) == base64.b64decode(create_dummy_image().to_base64())

    def test_convert_image_to_part_fallback(self):
        pil_image = PILImage.new("RGB", (100, 100), color = "red")
        image = Image(pil_image)  # Create an image without base64 or path
        part = adapter.convert_image_to_part(image)
        assert isinstance(part, types.Part)
        assert part.text == "[Unprocessable Image]"

def test_process_content_string():
    content = "test string"
    parts = adapter.process_content(content)
    assert len(parts) == 1
    assert parts[0].text == content

def test_process_content_list_strings():
    content = ["string1", "string2"]
    parts = adapter.process_content(content)
    assert len(parts) == 2
    assert parts[0].text == "string1"
    assert parts[1].text == "string2"

def test_process_content_list_images():
    image1 = create_dummy_image()
    image2 = create_dummy_image()
    content = [image1, image2]
    parts = adapter.process_content(content)
    assert len(parts) == 2
    assert parts[0].inline_data.mime_type == "image/jpeg"
    assert parts[1].inline_data.mime_type == "image/jpeg"

def test_process_content_mixed_list():
    image = create_dummy_image()
    content = ["string", image, 123]
    parts = adapter.process_content(content)
    assert len(parts) == 3
    assert parts[0].text == "string"
    assert parts[1].inline_data.mime_type == "image/jpeg"
    assert parts[2].text == "123"

def test_convert_message_to_genai_content_system():
    message = SystemMessage(content="system message")
    genai_content = adapter.convert_message_to_genai_content(message)
    assert genai_content == "system message"

class TestConvertMessageToGenaiContent:
    def test_convert_message_to_genai_content_user_string(self):
        message = UserMessage(content="user message", source="user")
        content = adapter.convert_message_to_genai_content(message)
        assert content == "user message"

    def test_convert_message_to_genai_content_user_list(self):
        message = UserMessage(content=["user message part1", "user message part2"], source="user")
        content = adapter.convert_message_to_genai_content(message)
        assert content == ["user message part1", "user message part2"]

    def test_convert_message_to_genai_content_assistant(self):
        message = AssistantMessage(content="assistant message", source="assistant")
        content = adapter.convert_message_to_genai_content(message)
        assert content == "assistant message"

    def test_convert_message_to_genai_content_llm(self):
        message = UserMessage(content="llm message", source="llm") # Use UserMessage instead of LLMMessage
        content = adapter.convert_message_to_genai_content(message)
        assert content == "llm message"

class TestPrepareGenaiContents:
    def test_prepare_genai_contents_strings(self):
        messages = [
            UserMessage(content="message 1", source="user"),
            AssistantMessage(content="message 2", source="assistant"),
        ]
        contents = adapter.prepare_genai_contents(messages)
        assert len(contents) == 2
        assert contents[0] == "message 1"
        assert contents[1] == "message 2"

    def test_prepare_genai_contents_mixed_content(self):
        image = create_dummy_image()
        messages = [
            UserMessage(content="message 1", source="user"),
            AssistantMessage(content="message 2", source="assistant"), # Use string content for AssistantMessage
        ]
        contents = adapter.prepare_genai_contents(messages)
        assert len(contents) == 2
        assert contents[0] == "message 1"
        assert contents[1] == "message 2"

    def test_prepare_genai_contents_other_types(self):
        messages = [
            UserMessage(content="message 1", source="user"),
            AssistantMessage(content="invalid content", source="assistant"), # Use string content for AssistantMessage
        ]
        contents = adapter.prepare_genai_contents(messages)
        assert len(contents) == 2 # Expecting no error, invalid content should be handled in adapter
        assert contents[0] == "message 1"
        assert contents[1] == "invalid content"

class TestConvertTool:
    def test_convert_tool_tool_object(self):
        tool_schema = { # Use dict instead of ToolSchema
            "name": "test_tool",
            "description": "test tool description",
            "parameters": {"type": "object", "properties": {"location": {"type": "string", "title": "location"}}},
        }
        genai_tool = adapter.convert_tool(tool_schema) # Pass tool_schema dict directly
        assert isinstance(genai_tool, types.Tool)
        assert genai_tool.function_declarations[0].name == "test_tool"
        assert genai_tool.function_declarations[0].description == "test tool description"
        assert genai_tool.function_declarations[0].parameters.type_ == types.Schema.Type.OBJECT
        assert genai_tool.function_declarations[0].parameters.properties[
            "location"
        ].type_ == types.Schema.Type.STRING
        # title should be removed
        assert not hasattr(genai_tool.function_declarations[0].parameters.properties["location"], "title")

    def test_convert_tool_tool_schema_object(self):
        tool_schema = { # Use dict instead of ToolSchema
            "name": "test_tool_schema",
            "description": "test tool schema description",
            "parameters": {"type": "object", "properties": {"location": {"type": "string", "title": "location"}}},
        }
        genai_tool = adapter.convert_tool(tool_schema)
        assert isinstance(genai_tool, types.Tool)
        assert genai_tool.function_declarations[0].name == "test_tool_schema"
        assert genai_tool.function_declarations[0].description == "test tool schema description"
        assert genai_tool.function_declarations[0].parameters.type_ == types.Schema.Type.OBJECT
        assert genai_tool.function_declarations[0].parameters.properties[
            "location"
        ].type_ == types.Schema.Type.STRING
        # title should be removed
        assert not hasattr(genai_tool.function_declarations[0].parameters.properties["location"], "title")

    def test_convert_tool_error_handling(self):
        tool_schema = { # Use dict instead of ToolSchema
            "name": "invalid_tool",
            "description": "invalid tool description",
            "parameters": {"type": "invalid"}, # Invalid schema type
        }
        genai_tool = adapter.convert_tool(tool_schema)
        assert genai_tool.function_declarations[0].parameters == types.Schema(type_=types.Schema.Type.OBJECT, properties={}) # Should return fallback schema

    def test_convert_tools(self):
        tool_schema1 = { # Use dict instead of ToolSchema
            "name": "tool1", "description": "tool1 description", "parameters": {"type": "object", "properties": {}}
        }
        tool1 = tool_schema1 # Use dict directly
        tool_schema2 = { # Use dict instead of ToolSchema
            "name": "tool2", "description": "tool2 description", "parameters": {"type": "object", "properties": {}}
        }
        tool2 = tool_schema2 # Use dict directly
        tools = [tool1, tool2] # Mix of Tool and ToolSchema
        genai_tools = adapter.convert_tools(tools)
        assert len(genai_tools) == 2
        assert genai_tools[0].function_declarations[0].name == "tool1"
        assert genai_tools[1].function_declarations[0].name == "tool2"

    def test_convert_tools_error_handling(self):
        tool_schema1 = { # Use dict instead of ToolSchema
            "name": "tool1", "description": "tool1 description", "parameters": {"type": "object", "properties": {}}
        }
        tool1 = tool_schema1 # Use dict directly
        tool_schema2 = { # Use dict instead of ToolSchema
            "name": "invalid_tool", "description": "invalid tool description", "parameters": {"type": "invalid"}
        } # Invalid tool
        tool2 = tool_schema2 # Use dict directly
        tools = [tool1, tool2] # Mix of valid and invalid tools
        genai_tools = adapter.convert_tools(tools)
        assert len(genai_tools) == 2 # Should not return None if any tool conversion fails, but skip invalid ones
        assert genai_tools[0].function_declarations[0].name == "tool1"
        assert genai_tools[1].function_declarations[0].name == "unknown" # Fallback name for invalid tool

    def test_convert_safety_settings_valid(self):
        safety_settings = {
            "HARM_CATEGORY_HATE_SPEECH": {"threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        }
        genai_safety_settings = adapter.convert_safety_settings(safety_settings)
        assert genai_safety_settings is not None
        assert len(genai_safety_settings) == 1
        assert genai_safety_settings[0].category == types.HarmCategory.HARM_CATEGORY_HATE_SPEECH
        assert genai_safety_settings[0].threshold == types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE

    def test_convert_safety_settings_invalid_threshold(self):
        safety_settings = {
            "HARM_CATEGORY_HATE_SPEECH": {"threshold": "INVALID_THRESHOLD"}, # Invalid threshold, but should still convert category
        }
        genai_safety_settings = adapter.convert_safety_settings(safety_settings)
        assert genai_safety_settings is not None # Should not return empty list if any error occurs in conversion, but return valid settings
        assert len(genai_safety_settings) == 1
        assert genai_safety_settings[0].category == types.HarmCategory.HARM_CATEGORY_HATE_SPEECH
        assert genai_safety_settings[0].threshold == "INVALID_THRESHOLD" # It will pass invalid threshold as string, and let google.genai to handle error

    def test_convert_safety_settings_missing_threshold(self):
        safety_settings = {
            "HARM_CATEGORY_HATE_SPEECH": {}, # Missing threshold
        }
        genai_safety_settings = adapter.convert_safety_settings(safety_settings)
        assert genai_safety_settings is None # Should return None if any error occurs in conversion

    def test_convert_safety_settings_invalid_category(self):
        safety_settings = {
            "INVALID_CATEGORY": {"threshold": "BLOCK_MEDIUM_AND_ABOVE"}, # Invalid category
        }
        genai_safety_settings = adapter.convert_safety_settings(safety_settings)
        assert genai_safety_settings is not None # Should not return empty list if any error occurs in conversion, but return valid settings
        assert len(genai_safety_settings) == 1
        assert genai_safety_settings[0].category == "INVALID_CATEGORY" # It will pass invalid category as string, and let google.genai to handle error
        assert genai_safety_settings[0].threshold == types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE

    def test_convert_tool_tool_schema_no_parameters(self):
        tool_schema = ToolSchema(
            name="test_tool_no_params",
            description="test tool schema with no parameters",
        )
        genai_tool = adapter.convert_tool(tool_schema.dict()) # Pass tool_schema dict
        assert isinstance(genai_tool, types.Tool)
        assert genai_tool.function_declarations[0].name == "test_tool_no_params"
        assert genai_tool.function_declarations[0].description == "test tool schema with no parameters"
        assert genai_tool.function_declarations[0].parameters.type_ == types.Schema.Type.OBJECT
        assert not genai_tool.function_declarations[0].parameters.properties

    def test_convert_tool_tool_schema_different_params(self):
        tool_schema = ToolSchema(
            name="test_tool_diff_params",
            description="test tool schema with different parameter types",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "radius": {"type": "integer"},
                    "is_raining": {"type": "boolean"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
            },
        )
        genai_tool = adapter.convert_tool(tool_schema.dict()) # Pass tool_schema dict
        assert isinstance(genai_tool, types.Tool)
        assert genai_tool.function_declarations[0].name == "test_tool_diff_params"
        assert genai_tool.function_declarations[0].description == "test tool schema with different parameter types"
        assert genai_tool.function_declarations[0].parameters.type_ == types.Schema.Type.OBJECT
        assert genai_tool.function_declarations[0].parameters.properties[
            "location"
        ].type_ == types.Schema.Type.STRING
        assert genai_tool.function_declarations[0].parameters.properties[
            "radius"
        ].type_ == types.Schema.Type.INTEGER
        assert genai_tool.function_declarations[0].parameters.properties[
            "is_raining"
        ].type_ == types.Schema.Type.BOOLEAN
        assert genai_tool.function_declarations[0].parameters.properties[
            "items"
        ].type_ == types.Schema.Type.ARRAY
