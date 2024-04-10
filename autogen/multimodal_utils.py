import re
import warnings
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union, runtime_checkable

from autogen.agentchat.contrib.img_utils import AGImage, gpt4v_formatter

IMPORTANT_KEYS = ["vision_model", "tool_calling", "json_object", "max_num_image"]


@runtime_checkable
class MultimodalObject(Protocol):
    def __init__(self, data: Union[str, Dict]):
        """
        The data can either be input file, input URL, or OpenAI format.

        Args:
            data (Union[str, Dict]): _description_
        """
        return

    def __str__(self):
        return self.__str__

    def __repr__(self) -> str:
        return self.__repr__

    @property
    def __dict__(self) -> Dict:
        return self.__dict__

    def openai_format(self) -> Dict:
        return {}


def convert_to_ag_format_list(content: Union[str, List, MultimodalObject], mm_tag_style: Optional[str] = None) -> List:
    """
    Converts input data to a standardized list format of AG objects. The input can be a JSON-formatted string,
    a dictionary representing a single item, or a list of dictionaries. This function standardizes these various
    formats into a consistent list of dictionaries formatted according to the AG specification, which might include
    converting string representations of data into structured AG format or wrapping single dictionaries into a list.

    The content can be either:
    1. a string, which may need mm_tag_style
    2. a list of string and MultimodalObject, which should be return as is
    3. a list of dictionaries in OpenAI message content format, which may need to be converted to a list of string and MultimodalObject.

    Args:
        content (Union[str, Dict, List[dict]]): The input data to convert.
        a dictionary (representing a single AG object), or a list of dictionaries (representing multiple AG objects).
        mm_tag_style (str): one of "html", "token", or None. If provided, the function will parse multimodal objects
            from the text using the specified format.
            Default to None, which means we do not parse the string to extract multimodal objects.

    Returns:
        List[dict]: A list of dictionaries, each formatted according to the AG specification. This format is designed
        for consistent processing and representation of data across the application.
    """
    # TODO: also handle audio, video, and other contents

    converted = []

    if isinstance(content, AGImage):
        # TODO: check other multimodal objects
        return [content.openai_format()]

    if isinstance(content, str):
        if mm_tag_style == "html":
            return gpt4v_formatter(content, img_format="pil", output_format="autogen", mm_tag_style="html")
        elif mm_tag_style == "tokenizer":
            # TODO: add parsing tokenzier later.
            return []
        else:
            return [content]

    assert isinstance(content, list), "content must be a list"

    if all(isinstance(x, dict) for x in content):
        # The input is openAI format
        for component in content:
            assert "type" in component, "type is required in message content"

            if component["type"] == "text":
                converted.append(component["text"])
            elif component["type"] == "image_url":
                # TODO: recursive import, how to define AGImage here?
                converted.append(AGImage(component["image_url"]["url"]))
        return converted

    if all(isinstance(x, str) or isinstance(x, AGImage) for x in content):
        # TODO: check other multimodal objects
        # The input is already in AG format
        return content

    raise ValueError("Invalid content format")


def ag_params_to_openai(params: Dict) -> Dict:
    # Get the important parameters
    messages = params.get("messages", []).copy()
    model_name = params.get("model", None)

    # Pop AG parameters, which are not needed for OpenAI
    is_vision_model = params.pop("vision_model", False)
    tool_calling = params.pop("tool_call", True)
    json_object = params.pop("json_object", True)
    max_num_image = params.pop("max_num_image", 1e9)

    n_img_count = 0
    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]

        # iterate in reverse order to remove "extra" multimodal objects so that
        assert "role" in message, "role is required in message"
        assert "content" in message, "content is required in message"

        content = message["content"]
        if isinstance(content, str):
            continue  # str in standard LLM format. Skip formatting
        if isinstance(content, list):
            content = content.copy()
            for j, component in enumerate(content):
                if isinstance(component, str):
                    content[j] = {"type": "text", "text": component}
                elif isinstance(component, MultimodalObject):
                    if is_vision_model:
                        n_img_count += 1
                        if n_img_count > max_num_image:
                            content[j] = ""
                        else:
                            content[j] = component.openai_format()
                    else:
                        content[j] = ""  # mark to remove
                        warnings.warn(f"images are skipped in {model_name}!")
                elif isinstance(component, dict):
                    # it is already OpenAI format
                    continue
                else:
                    raise ValueError(f"Invalid component type in message content: {type(component)}")

            messages[i]["content"] = [x for x in content if x]

        if not tool_calling:
            # remove tool call-related keys in the message if present
            func_keys = ["tool_calls", "tool_responses", "function_call", "tool_call_id"]
            if any(message.pop(p, False) for p in func_keys):
                warnings.warn(f"tool_calls and tool_responses are skipped in {model_name}.")
                message["role"] = "user"

    if not json_object:
        if params.get("response_format", None) == {"type": "json_object"}:
            warnings.warn(f"response_format of JSON object is skipped in {model_name}.")
            params.pop("response_format")

    return params
