from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str
