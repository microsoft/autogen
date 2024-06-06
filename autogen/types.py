from typing import Dict, List, Literal, TypedDict, Union

MessageContentType = Union[str, List[Union[Dict, str]], None]


class UserMessageTextContentPart(TypedDict):
    type: Literal["text"]
    text: str


class UserMessageImageContentPart(TypedDict):
    type: Literal["image_url"]
    # Ignoring the other "detail param for now"
    image_url: Dict[Literal["url"], str]
