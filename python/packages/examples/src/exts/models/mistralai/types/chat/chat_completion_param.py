

from typing_extensions import TypedDict,Required,Literal


__all__=["ChatCompletionContentPartTextParam"]

class ChatCompletionContentPartTextParam(TypedDict, total=False):
    text: Required[str]
    """The text content."""

    type: Required[Literal["text"]]
    """The type of the content part."""
