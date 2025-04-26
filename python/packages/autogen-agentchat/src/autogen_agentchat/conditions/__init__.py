"""
This module provides various termination conditions for controlling the behavior of
multi-agent teams.
"""

from ._terminations import (
    ExternalTermination,
    FunctionalTermination,
    FunctionCallTermination,
    HandoffTermination,
    MaxMessageTermination,
    SourceMatchTermination,
    StopMessageTermination,
    TextMentionTermination,
    TextMessageTermination,
    TimeoutTermination,
    TokenUsageTermination,
)

__all__ = [
    "MaxMessageTermination",
    "TextMentionTermination",
    "StopMessageTermination",
    "TokenUsageTermination",
    "HandoffTermination",
    "TimeoutTermination",
    "ExternalTermination",
    "SourceMatchTermination",
    "TextMessageTermination",
    "FunctionCallTermination",
    "FunctionalTermination",
]
