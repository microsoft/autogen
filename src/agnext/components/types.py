from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


@dataclass
class FunctionSignature:
    name: str
    parameters: Dict[str, Any]
    description: str
