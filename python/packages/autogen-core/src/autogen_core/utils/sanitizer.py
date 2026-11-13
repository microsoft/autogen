def sanitize_tool_calls(message: dict) -> dict:
    """
    Validates tool_calls from LLM response. Raises error on known malformed patterns.
    """
    tool_calls = message.get("tool_calls", [])
    content = message.get("content", "")

    # Block empty tool_calls list
    if isinstance(tool_calls, list) and len(tool_calls) == 0:
        raise ValueError("Malformed tool call: tool_calls is an empty list.")

    # Block spurious tool_call_end marker
    if isinstance(content, str) and content.strip() == "<|tool_call_end|>":
        raise ValueError(" Invalid content-only tool call marker received.")

    return message
