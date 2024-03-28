import re
from typing import Any, Callable, Dict, List, Tuple, Union

from .agent import Agent


def consolidate_chat_info(chat_info, uniform_sender=None) -> None:
    if isinstance(chat_info, dict):
        chat_info = [chat_info]
    for c in chat_info:
        if uniform_sender is None:
            assert "sender" in c, "sender must be provided."
            sender = c["sender"]
        else:
            sender = uniform_sender
        assert "recipient" in c, "recipient must be provided."
        summary_method = c.get("summary_method")
        assert (
            summary_method is None
            or isinstance(summary_method, Callable)
            or summary_method in ("last_msg", "reflection_with_llm")
        ), "summary_method must be a string chosen from 'reflection_with_llm' or 'last_msg' or a callable, or None."
        if summary_method == "reflection_with_llm":
            assert (
                sender.client is not None or c["recipient"].client is not None
            ), "llm client must be set in either the recipient or sender when summary_method is reflection_with_llm."


def gather_usage_summary(agents: List[Agent]) -> Tuple[Dict[str, any], Dict[str, any]]:
    r"""Gather usage summary from all agents.

    Args:
        agents: (list): List of agents.

    Returns:
        tuple: (total_usage_summary, actual_usage_summary)

    Example:

    ```python
    total_usage_summary = {
        "total_cost": 0.0006090000000000001,
        "gpt-35-turbo": {
                "cost": 0.0006090000000000001,
                "prompt_tokens": 242,
                "completion_tokens": 123,
                "total_tokens": 365
        }
    }
    ```

    Note:

    `actual_usage_summary` follows the same format.
    If none of the agents incurred any cost (not having a client), then the total_usage_summary and actual_usage_summary will be `{'total_cost': 0}`.
    """

    def aggregate_summary(usage_summary: Dict[str, Any], agent_summary: Dict[str, Any]) -> None:
        if agent_summary is None:
            return
        usage_summary["total_cost"] += agent_summary.get("total_cost", 0)
        for model, data in agent_summary.items():
            if model != "total_cost":
                if model not in usage_summary:
                    usage_summary[model] = data.copy()
                else:
                    usage_summary[model]["cost"] += data.get("cost", 0)
                    usage_summary[model]["prompt_tokens"] += data.get("prompt_tokens", 0)
                    usage_summary[model]["completion_tokens"] += data.get("completion_tokens", 0)
                    usage_summary[model]["total_tokens"] += data.get("total_tokens", 0)

    total_usage_summary = {"total_cost": 0}
    actual_usage_summary = {"total_cost": 0}

    for agent in agents:
        if getattr(agent, "client", None):
            aggregate_summary(total_usage_summary, agent.client.total_usage_summary)
            aggregate_summary(actual_usage_summary, agent.client.actual_usage_summary)

    return total_usage_summary, actual_usage_summary


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
