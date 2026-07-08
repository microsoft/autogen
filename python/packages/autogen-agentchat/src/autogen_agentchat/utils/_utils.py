from typing import List, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import FunctionExecutionResult, LLMMessage, UserMessage
from pydantic import BaseModel

# Type aliases for convenience
_StructuredContent = BaseModel
_UserContent = Union[str, List[Union[str, Image]]]
_AssistantContent = Union[str, List[FunctionCall]]
_FunctionExecutionContent = List[FunctionExecutionResult]
_SystemContent = str


def content_to_str(
    content: _UserContent | _AssistantContent | _FunctionExecutionContent | _SystemContent | _StructuredContent,
) -> str:
    """Convert the content of an LLMMessage to a string."""
    if isinstance(content, str):
        return content
    elif isinstance(content, BaseModel):
        return content.model_dump_json()
    else:
        result: List[str] = []
        for c in content:
            if isinstance(c, str):
                result.append(c)
            elif isinstance(c, Image):
                result.append("<image>")
            else:
                result.append(str(c))

    return "\n".join(result)


def remove_images(messages: List[LLMMessage]) -> List[LLMMessage]:
    """Remove images from a list of LLMMessages"""
    str_messages: List[LLMMessage] = []
    for message in messages:
        if isinstance(message, UserMessage) and isinstance(message.content, list):
            str_messages.append(UserMessage(content=content_to_str(message.content), source=message.source))
        else:
            str_messages.append(message)
    return str_messages
