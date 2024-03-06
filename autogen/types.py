from typing import Dict, Literal, TypedDict


class UserMessageTextContentPart(TypedDict):
    type: Literal["text"]
    text: str


class UserMessageImageContentPart(TypedDict):
    type: Literal["image_url"]
    # Ignoring the other "detail param for now"
    image_url: Dict[Literal["url"], str]


class SystemMessage(TypedDict):
    content: str
    role: Literal["system"]
