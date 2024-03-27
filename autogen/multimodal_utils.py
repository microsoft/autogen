import re
from typing import Any, Callable, Dict, List, Tuple, Union


def parse_tags_from_content(tag: str, content: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Dict[str, str]]]:
    """Parses HTML style tags from message contents.

    The parsing is done by looking for patterns in the text that match the format of HTML tags. The tag to be parsed is
    specified as an argument to the function. The function looks for this tag in the text and extracts its content. The
    content of a tag is everything that is inside the tag, between the opening and closing angle brackets. The content
    can be a single string or a set of attribute-value pairs.

    Examples:
        <img http://example.com/image.png> -> [{"tag": "img", "attr": {"src": "http://example.com/image.png"}, "match": re.Match}]
        <audio text="Hello I'm a robot" prompt="whisper"> ->
                [{"tag": "audio", "attr": {"text": "Hello I'm a robot", "prompt": "whisper"}, "match": re.Match}]

    Args:
        tag (str): The HTML style tag to be parsed.
        content (Union[str, List[Dict[str, Any]]]): The message content to parse. Can be a string or a list of content
            items.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, where each dictionary represents a parsed tag. Each dictionary
            contains three key-value pairs: 'type' which is the tag, 'attr' which is a dictionary of the parsed attributes,
            and 'match' which is a regular expression match object.

    Raises:
        ValueError: If the content is not a string or a list.
    """
    results = []
    if isinstance(content, str):
        results.extend(_parse_tags_from_text(tag, content))
    # Handles case for multimodal messages.
    elif isinstance(content, list):
        for item in content:
            if item.get("type") == "text":
                results.extend(_parse_tags_from_text(tag, item["text"]))
    else:
        raise ValueError(f"content must be str or list, but got {type(content)}")

    return results


def _parse_tags_from_text(tag: str, text: str) -> List[Dict[str, str]]:
    pattern = re.compile(f"<{tag} (.*?)>")

    results = []
    for match in re.finditer(pattern, text):
        tag_attr = match.group(1).strip()
        attr = _parse_attributes_from_tags(tag_attr)

        results.append({"tag": tag, "attr": attr, "match": match})
    return results


def _parse_attributes_from_tags(tag_content: str):
    pattern = r"([^ ]+)"
    attrs = re.findall(pattern, tag_content)
    reconstructed_attrs = _reconstruct_attributes(attrs)

    def _append_src_value(content, value):
        if "src" in content:
            content["src"] += f" {value}"
        else:
            content["src"] = value

    content = {}
    for attr in reconstructed_attrs:
        if "=" not in attr:
            _append_src_value(content, attr)
            continue

        key, value = attr.split("=", 1)
        if value.startswith("'") or value.startswith('"'):
            content[key] = value[1:-1]  # remove quotes
        else:
            _append_src_value(content, attr)

    return content


def _reconstruct_attributes(attrs: List[str]) -> List[str]:
    """Reconstructs attributes from a list of strings where some attributes may be split across multiple elements."""

    def is_attr(attr: str) -> bool:
        if "=" in attr:
            _, value = attr.split("=", 1)
            if value.startswith("'") or value.startswith('"'):
                return True
        return False

    reconstructed = []
    found_attr = False
    for attr in attrs:
        if is_attr(attr):
            reconstructed.append(attr)
            found_attr = True
        else:
            if found_attr:
                reconstructed[-1] += f" {attr}"
                found_attr = True
            elif reconstructed:
                reconstructed[-1] += f" {attr}"
            else:
                reconstructed.append(attr)
    return reconstructed
