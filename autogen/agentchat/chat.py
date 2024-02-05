import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """(Experimental) The result of a chat. Almost certain to be changed."""

    chat_history: List[Dict[str, any]] = None
    summary: str = None
    cost: dict = None  # (dict, dict) - (total_cost, actual_cost_with_cache)
    human_input: List[str] = None
