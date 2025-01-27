from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


@dataclass
class FunctionCalls:
    function_calls: List[FunctionCall]
    thought: Optional[str] = None
