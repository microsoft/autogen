import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """(In preview) A dataclass to store the result of a chat."""

    chat_history: List[Dict[str, any]]
    summary: str = None
    cost: dict = None  # (dict, dict) - (total_cost, actual_cost_with_cache)
    human_input: List[str] = None
