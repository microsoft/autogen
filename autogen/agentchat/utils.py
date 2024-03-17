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


def parse_tags_from_content(
    tag: str, content: Union[str, List[Dict[str, Any]]]
) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """Parses HTML style tags from message contents.

    The parsing is done by looking for patterns in the text that match the format of HTML tags. The tag to be parsed is
    specified as an argument to the function. The function looks for this tag in the text and extracts its content. The
    content of a tag is everything that is inside the tag, between the opening and closing angle brackets. The content
    can be a single string or a set of attribute-value pairs.

    Args:
        tag (str): The HTML style tag to be parsed.
        content (Union[str, List[Dict[str, Any]]]): The message content to parse. Can be a string or a list of content
            items.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, where each dictionary represents a parsed tag. Each dictionary
            contains two key-value pairs: 'type' which is the tag, and 'content' which is a dictionary of the parsed
            attributes.

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
    pattern = f"<{tag} (.*?)>"
    tag_contents = re.findall(pattern, text)

    results = []
    for tag_content in tag_contents:
        content = _parse_attributes_from_tags(tag_content)
        results.append({"tag": tag, "content": content})

    return results


def _parse_attributes_from_tags(tag_content: str):
    # Find all attribute-value pairs and standalone words in the tag content
    attributes = re.findall(r'[^=\s]*="[^"]*"|[^=\s]*=\'[^\']*\'|\S+', tag_content)
    content = {}
    src_found = False
    for attribute in attributes:
        if "=" in attribute:
            key, value = attribute.split("=", 1)
            content[key] = value.strip("'\"")
        else:
            # If the attribute does not include an equals sign, assume it's the src
            if not src_found:
                content["src"] = attribute
                src_found = True
    return content
