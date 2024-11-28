from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BaseState:
    """Base class for all saveable state"""
    state_type: str  # To validate correct state type when loading
    version: str = "1.0.0"

    def __post_init__(self):
        if not self.state_type.isidentifier():
            raise ValueError(
                f"state_type must be a valid identifier: {self.state_type}")
