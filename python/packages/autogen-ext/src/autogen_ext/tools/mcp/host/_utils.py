import base64
import io
from typing import Any, Dict

from autogen_core import Image
from autogen_core.models import (
    AssistantMessage,
    FinishReasons,
    LLMMessage,
    ModelInfo,
    UserMessage,
)
from PIL import Image as PILImage

from mcp import types as mcp_types
from mcp.types import StopReason


def parse_sampling_content(
    content: mcp_types.TextContent | mcp_types.ImageContent | mcp_types.AudioContent,
    model_info: ModelInfo | None = None,
) -> str | Image:
    """Convert MCP content types to AutoGen content types.

    Handles text and image content conversion, with vision model validation for images.

    Args:
        content: MCP content object (text, image, or audio)
        model_info: Optional model information for vision capability checking

    Returns:
        Converted content as string or Image object

    Raises:
        RuntimeError: If image content is provided but model doesn't support vision
        ValueError: If content type is unsupported
    """
    if content.type == "text":
        return content.text
    elif content.type == "image":
        if model_info and not model_info.get("vision", False):
            model_family = model_info.get("family", "unknown")
            raise RuntimeError(f"model {model_family} does not support vision.")

        # Decode base64 image data and create PIL Image
        image_data = base64.b64decode(content.data)
        pil_image = PILImage.open(io.BytesIO(image_data))
        return Image.from_pil(pil_image)
    else:
        raise ValueError(f"Unsupported content type: {content.type}")


def parse_sampling_message(message: mcp_types.SamplingMessage, model_info: ModelInfo | None = None) -> LLMMessage:
    """Convert MCP sampling messages to AutoGen LLM messages.

    Args:
        message: MCP sampling message with role and content
        model_info: Optional model information for content parsing

    Returns:
        Converted AutoGen LLM message (UserMessage or AssistantMessage)

    Raises:
        ValueError: If message role is not recognized
        AssertionError: If assistant message content is not text
    """
    content = parse_sampling_content(message.content, model_info=model_info)
    if message.role == "user":
        return UserMessage(
            source="user",
            content=[content],
        )
    elif message.role == "assistant":
        assert isinstance(content, str), "Assistant messages only support string content."
        return AssistantMessage(
            source="assistant",
            content=content,
        )
    else:
        raise ValueError(f"Unrecognized message role: {message.role}")


def finish_reason_to_stop_reason(finish_reason: FinishReasons) -> StopReason:
    """Convert AutoGen finish reasons to MCP stop reasons.

    Args:
        finish_reason: AutoGen completion finish reason

    Returns:
        Corresponding MCP stop reason
    """
    if finish_reason == "stop":
        return "endTurn"
    elif finish_reason == "length":
        return "maxTokens"
    else:
        return finish_reason


def create_request_params_to_extra_create_args(params: mcp_types.CreateMessageRequestParams) -> Dict[str, Any]:
    """Convert MCP request parameters to AutoGen extra create arguments.

    Args:
        params: MCP message creation request parameters

    Returns:
        Dictionary of extra arguments for AutoGen chat completion client
    """
    # TODO: Need to support all ChatCompletionClients
    extra_create_args: dict[str, Any] = {"max_tokens": params.maxTokens}
    if params.temperature is not None:
        extra_create_args["temperature"] = params.temperature
    if params.stopSequences is not None:
        extra_create_args["stop"] = params.stopSequences
    return extra_create_args
