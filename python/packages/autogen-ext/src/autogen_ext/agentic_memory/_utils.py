from typing import Any, Dict, List, Union, Tuple

from autogen_core import FunctionCall, Image
from autogen_core.models import FunctionExecutionResult, LLMMessage

# Convenience types
UserContent = Union[str, List[Union[str, Image]]]
AssistantContent = Union[str, List[FunctionCall]]
FunctionExecutionContent = List[FunctionExecutionResult]
SystemContent = str
MessageContent = UserContent | AssistantContent | SystemContent | FunctionExecutionContent


def message_content_to_str(message_content: MessageContent) -> str:
    """
    Converts the message content to a string.
    """
    if message_content is None:
        return ""
    elif isinstance(message_content, str):
        return message_content
    elif isinstance(message_content, List):
        converted: List[str] = list()
        for item in message_content:
            if isinstance(item, str):
                converted.append(item)
            elif isinstance(item, Image):
                converted.append("<Image>")
            else:
                converted.append(str(item).rstrip())
        return "\n".join(converted)
    else:
        raise AssertionError("Unexpected response type.")


def text_from_user_content(user_content: UserContent) -> str:
    """
    Extracts just the text from the user content.
    """
    if isinstance(user_content, str):
        return user_content
    elif isinstance(user_content, List):
        text_list: List[str] = list()
        for item in user_content:
            if isinstance(item, str):
                text_list.append(item.rstrip())
        return "\n\n".join(text_list)
    else:
        raise AssertionError("Unexpected response type.")


def single_image_from_user_content(user_content: UserContent) -> Union[Image, None]:
    """
    Extracts a single image from the user content.
    """
    image_to_return = None
    if isinstance(user_content, str):
        return None
    elif isinstance(user_content, List):
        for item in user_content:
            if isinstance(item, Image):
                assert image_to_return is None, "Only one image is currently allowed in the user content."
                image_to_return = item
    else:
        raise AssertionError("Unexpected response type.")
    return image_to_return
