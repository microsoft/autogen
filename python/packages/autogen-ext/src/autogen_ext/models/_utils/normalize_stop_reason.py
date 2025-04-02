from typing import Dict

from autogen_core.models import FinishReasons


def normalize_stop_reason(stop_reason: str | None) -> FinishReasons:
    if stop_reason is None:
        return "unknown"

    # Convert to lower case
    stop_reason = stop_reason.lower()

    KNOWN_STOP_MAPPINGS: Dict[str, FinishReasons] = {
        "stop": "stop",
        "length": "length",
        "content_filter": "content_filter",
        "function_calls": "function_calls",
        "end_turn": "stop",
        "tool_calls": "function_calls",
    }

    return KNOWN_STOP_MAPPINGS.get(stop_reason, "unknown")
