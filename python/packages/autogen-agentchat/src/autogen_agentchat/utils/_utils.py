from typing import List

from autogen_core import Image
from autogen_core.models import LLMMessage, UserMessage


def _image_content_to_str(content: str | List[str | Image]) -> str:
    """Convert the content of an LLMMessageto a string."""
    if isinstance(content, str):
        return content
    else:
        result: List[str] = []
        for c in content:
            if isinstance(c, str):
                result.append(c)
            elif isinstance(c, Image):
                result.append("<image>")
            else:
                raise AssertionError("Received unexpected content type.")

    return "\n".join(result)


def remove_images(messages: List[LLMMessage]) -> List[LLMMessage]:
    """Remove images from a list of LLMMessages"""
    str_messages: List[LLMMessage] = []
    for message in messages:
        if isinstance(message, UserMessage) and isinstance(message.content, list):
            str_messages.append(UserMessage(content=_image_content_to_str(message.content), source=message.source))
        else:
            str_messages.append(message)
    return str_messages
