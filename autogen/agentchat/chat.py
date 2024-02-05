import logging
from typing import Dict, List, TypedDict

logger = logging.getLogger(__name__)


class ChatResult(TypedDict):
    """(Experimental) The result of a chat. Almost certain to be changed."""

    chat_history: List[Dict[str, any]]
    summary: str
    cost: dict  # (dict, dict) - (total_cost, actual_cost_with_cache)
    human_input: List[str]
